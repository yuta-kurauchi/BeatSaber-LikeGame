import cv2
import mediapipe as mp
import numpy as np
import socket
import json
import os

# MediaPipe Tasks APIのインポート
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

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
smoothed_vector = {0: None, 1: None, 9: None, 17: None}
Smoothed_vector = {0: None}

# numpyベクトルで平滑化
def to_np(lm_x, lm_y, lm_z, id, is_world=True):
    raw_vector = np.array([lm_x, lm_y, lm_z])
    target_dict = smoothed_vector if is_world else Smoothed_vector
    
    if target_dict[id] is None:
        target_dict[id] = raw_vector
    else:
        target_dict[id] = alpha * raw_vector + (1 - alpha) * target_dict[id]
    return target_dict[id]


def scale(Pos_np, h, w):
    scale_np = Pos_np.copy()
    scale_np[0] *= w
    scale_np[1] *= -h  # 反転解除とスケーリング
    return scale_np

def reSetVector():
    smoothed_vector[0] = None
    smoothed_vector[1] = None
    smoothed_vector[9] = None
    smoothed_vector[17] = None
    Smoothed_vector[0] = None

def calc_v(id, landmarks, w_np):
    # hand_world_landmarks から指定IDの座標を取得
    lm = landmarks[id]
    np_array = to_np(lm.x, lm.y, lm.z, id, is_world=True)
    vector = np_array - w_np
    vector[1] *= -1  # y軸反転
    return vector

def calc_nv(va, vb):
    return np.cross(va, vb)

# カメラ設定（0か1、環境に合わせて変更してください）
cap = cv2.VideoCapture(0)
init_udp_socket()

# -------------------------------------------------------------------------
# MediaPipe Tasks APIの初期化設定
# -------------------------------------------------------------------------
model_path = os.path.join(os.path.dirname(__file__), 'hand_landmarker.task')
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE, # 1フレームずつ処理するモード
    num_hands=1,                           # 片手のみ検出
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

        # 検出実行（新仕様の呼び出し方）
        results = landmarker.detect(mp_image)
        # 検出してからイメージを反転
        image = cv2.flip(image, 1)

        # 描画用にBGRに戻す
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 手が検出された場合、Unityへの送信データを作成
        if results.hand_landmarks:
            # 1つ目の手（片手設定なのでindexは0固定）
            hand_landmarks = results.hand_landmarks[0]
            hand_world_landmarks = results.hand_world_landmarks[0]
            handedness = results.handedness[0][0]

            # 手首(ID:0)の座標を取得
            wrist_world = hand_world_landmarks[0]
            wrist_normal = hand_landmarks[0]

            wrist_np = to_np(wrist_world.x, wrist_world.y, wrist_world.z, 0, is_world=True)
            wrist_np_notWorld = to_np(wrist_normal.x, wrist_normal.y, wrist_normal.z, 0, is_world=False)
            
            # リアルスケール座標計算
            # これのせいでカメラの比によって移動が異なる
            wristPos_rial = scale(wrist_np_notWorld, height, width)

            # 各指への相対ベクトル計算
            thumb_v = calc_v(1, hand_world_landmarks, wrist_np)
            middleF_v = calc_v(9, hand_world_landmarks, wrist_np)
            pinky_v = calc_v(17, hand_world_landmarks, wrist_np)

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