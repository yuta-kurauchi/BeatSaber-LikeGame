import cv2
import mediapipe as mp
import numpy as np
import socket
import json
import os

# MediaPipe Tasks APIのインポート
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 送信内容(UDP通信)
# {
#     "wristPos": [0.0, 0.0, 0.0],    // 手首の正規化スケールスクリーン座標 (X, Y, Z)
#     "palmNormal": [0.0, 0.0, 0.0],  // 掌の法線ベクトル（手の向き・傾き計算用）
#     "middleVec": [0.0, 0.0, 0.0],   // 手首から中指へのベクトル(正規化スクリーン座標)（手の回転方向計算用）
#     "isRight": true                 // 右手判定: true / 左手判定: false
# }

# MediaPipeLandMarkデータ


# 通信用設定
UNITY_HOST = "127.0.0.1"
UNITY_PORT = 50001
udp_sock = None

# ソケットの初期化
def init_udp_socket():
    global udp_sock
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"UDP通信を初期化しました。({UNITY_HOST}/{UNITY_PORT})")
        return True
    except Exception as e:
        print(f"UDP初期化失敗: {e}")
        return False

# unityへ送信
def send_to_unity(message):
    if not udp_sock:
        return False
    try:
        json_message = json.dumps(message)
        udp_sock.sendto(json_message.encode('utf-8'), (UNITY_HOST, UNITY_PORT))
        return True
    except Exception as e:
        print(f"UDP送信エラー: {e}")
        return False

# 指数移動平均（EMA）用設定
alpha = 0.2
screen_smoothed_vector = {0: None, 1: None, 9: None, 17: None}
world_smoothed_vector = {0: None}

# numpyベクトルで平滑化
# デフォルトはscreen座標
def to_np(lm_x, lm_y, lm_z, id, is_world=True):
    raw_vector = np.array([lm_x, lm_y, lm_z])
    # 値A if 条件 else 値B
    # もし 条件 が True なら 値A を、False なら 値B を代入する
    # 逆だとできている
    target_dict = screen_smoothed_vector if is_world else world_smoothed_vector
    
    if target_dict[id] is None:
        target_dict[id] = raw_vector
    else:
        target_dict[id] = alpha * raw_vector + (1 - alpha) * target_dict[id]
    return target_dict[id]

# numpy配列を返す
def to_numpy_array(lm):
    return np.array([lm.x,lm.y,lm.z])

def ema_func(raw_vector, id, is_world=True):
    # 値A if 条件 else 値B
    # もし 条件 が True なら 値A を、False なら 値B を代入する
    # 逆だとできている
    target_dict = screen_smoothed_vector if is_world else world_smoothed_vector
    
    if target_dict[id] is None:
        target_dict[id] = raw_vector
    else:
        target_dict[id] = alpha * raw_vector + (1 - alpha) * target_dict[id]
    return target_dict[id]

# スケールの調整 ここを変更する必要があるかも、
def scale(Pos_np, h, w):
    scale_np = Pos_np.copy()
    scale_np[0] *= w
    scale_np[1] *= -h  # 反転解除とスケーリング
    return scale_np

# smoothed_vectorのリセット用,手が画面から外れた時など。
def reSetVector():
    screen_smoothed_vector[0] = None
    screen_smoothed_vector[1] = None
    screen_smoothed_vector[9] = None
    screen_smoothed_vector[17] = None
    world_smoothed_vector[0] = None

# ここで平滑化しないようにする
# 手首からの相対ベクトルに変換するだけにする。
def calc_v(id, landmarks, w_np):
    # hand_world_landmarks から指定IDの座標を取得
    lm = landmarks[id]
    np_array = to_np(lm.x, lm.y, lm.z, id, is_world=True)
    vector = np_array - w_np
    vector[1] *= -1  # y軸反転
    return vector

# 手のひらの法線ベクトルを返す
def calc_nv(va, vb):
    return np.cross(va, vb)

# カメラ設定（0か1、環境に合わせて変更してください）
# 開発者の場合、macでは1,windowsでは0
if os.name == 'nt':
    cap = cv2.VideoCapture(0)
else:
    cap = cv2.VideoCapture(1)
init_udp_socket()

# MediaPipe Tasks APIの初期化設定
model_path = os.path.join(os.path.dirname(__file__), 'hand_landmarker.task')
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE, # The mode for single image inputs.
    num_hands=1,                           # 片手のみ検出,いずれは両手で動くようにする。
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5
)

# Tasks APIの検出器を作成
with vision.HandLandmarker.create_from_options(options) as landmarker:
    print("MediaPipe Tasks API が正常に起動しました。")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue

        # OpenCVはBGRなのでRGBに変換
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = image.shape

        # Tasks API用にMediaPipeのImageオブジェクトに変換
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)

        # 検出実行
        results = landmarker.detect(mp_image)
        # 検出してからイメージを反転
        image = cv2.flip(image, 1)

        # 描画用にBGRに戻す
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 手が検出された場合、Unityへの送信データを作成
        if results.hand_landmarks and results.hand_world_landmarks:
            # 1つ目の手（片手設定なのでindexは0固定） あとで両手対応にする
            hand_landmarks = results.hand_landmarks[0]
            hand_world_landmarks = results.hand_world_landmarks[0]
            handedness = results.handedness[0][0]

            # 手首(ID:0)の座標を取得
            wrist_world = hand_world_landmarks[0]
            wrist_normal = hand_landmarks[0]
            
            # 平滑化
            wrist_world_np = ema_func(to_numpy_array(wrist_world), 0, is_world=True)
            wrist_np = ema_func(to_numpy_array(wrist_normal), 0, is_world=False)

            # リアルスケール座標計算
            # これのせいでカメラの比によって移動が異なる
            wristPos_rial = scale(wrist_np, height, width)

            # 各指への相対ベクトル計算
            thumb_v = calc_v(1, hand_world_landmarks, wrist_world_np)
            middleF_v = calc_v(9, hand_world_landmarks, wrist_world_np)
            pinky_v = calc_v(17, hand_world_landmarks, wrist_world_np)

            # 左右判定と法線ベクトル計算
            label = handedness.category_name # "Left" or "Right"
            if label == "Right":
                isRight = True
                palm_nv = calc_nv(thumb_v, pinky_v)
            else:
                isRight = False
                palm_nv = calc_nv(pinky_v, thumb_v)

            # 旧コードの描画処理の代わりに簡易テキスト表示
            cv2.putText(image_bgr, f"{label} Hand", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Unityが待っているデータ構造（JSON辞書）を作成
            data_dict = {
                "wristPos": wristPos_rial.tolist(),
                "palmNormal": palm_nv.tolist(),
                "middleVec": middleF_v.tolist(),
                "isRight": isRight
            }

            # UDP送信
            send_to_unity(data_dict)
        else:
            reSetVector()

        # ウィンドウ表示
        cv2.imshow('MediaPipe Tasks Hand Tracking', image_bgr)

        if cv2.waitKey(5) & 0xFF == 27: # ESCキーで終了
            break

cap.release()
cv2.destroyAllWindows()
if udp_sock:
    udp_sock.close()