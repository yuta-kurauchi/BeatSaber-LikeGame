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
#     "wristPos": [0.0, 0.0, 0.0],    // 手首の正規化スクリーン座標 (X, Y, Z)
#     "palmNormal": [0.0, 0.0, 0.0],  // 掌の法線ベクトル（手の向き・傾き計算用）(ワールド座標)
#     "middleVec": [0.0, 0.0, 0.0],   // 手首から中指へのベクトル（手の回転方向計算用）(ワールド座標)
#     "isRight": true                 // 右手判定: true / 左手判定: false
# }

# 座標系の注意
# OpenCVは左上が原点
# MediaPipeは右上が原点
# Unityのviewport座標は左下が原点


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
world_smoothed_vector = {0: None, 1: None, 9: None, 17: None}
screen_smoothed_vector = {0: None, 1:None, 9: None, 17: None}

# numpy配列を返す
def to_numpy_array_screen(lm):
    # x,y座標を左下を(0,0)にする
    x = 1-lm.x
    y = 1-lm.y
    # x
    if x < 0:
        x = 0
    elif x > 1:
        x = 1
    # y   
    if y < 0:
        y = 0
    elif y > 1:
        y = 1       
    return np.array([x,y,lm.z])

# numpy配列を返す
def to_numpy_array(lm):
    # 左下を0に
    return np.array([-lm.x,-lm.y,lm.z])

# 平滑化_指数移動平均（EMA）
def ema_func(raw_vector, id, is_world=True):
    # 値A if 条件 else 値B
    # もし 条件 が True なら 値A を、False なら 値B を代入する
    target_dict = world_smoothed_vector if is_world else screen_smoothed_vector
    
    if target_dict[id] is None:
        target_dict[id] = raw_vector
    else:
        target_dict[id] = alpha * raw_vector + (1 - alpha) * target_dict[id]
    return target_dict[id]

# smoothed_vectorのリセット用,手が画面から外れた時など。
def reSetVector():
    world_smoothed_vector[0] = None
    world_smoothed_vector[1] = None
    world_smoothed_vector[9] = None
    world_smoothed_vector[17] = None
    screen_smoothed_vector[0] = None
    screen_smoothed_vector[1] = None
    screen_smoothed_vector[9] = None
    screen_smoothed_vector[17] = None

# 相対ベクトルab
def calc_relative_vector_ab(a_vec,b_vec):
    relative_vec = b_vec - a_vec
    # relative_vec[1] *= -1  # y軸反転
    return relative_vec

# 外積a×b
def calc_cross_np(va, vb):
    return np.cross(va, vb)

# pixel_coordinate
# 正規化座標をピクセルサイズを用いてピクセル座標へ
# 平滑化されたnumpyarrayが入ってくるので、座標調整のために、y軸反転してから、+ height
def to_pixel_coordinate(normal):
    px = int(normal[0] * width)
    py = int(normal[1] * height) * -1 + height
    return (px, py)

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

            # 座標を取得
            wrist_world = hand_world_landmarks[0]
            wrist_normal = hand_landmarks[0]
            thumb_normal = hand_landmarks[1]
            thumb_world = hand_world_landmarks[1]
            middle_normal = hand_landmarks[9]
            middle_world = hand_world_landmarks[9]
            pinky_normal = hand_landmarks[17]
            pinky_world = hand_world_landmarks[17]


            # 平滑化して、numpy配列で出力
            wrist_np = ema_func(to_numpy_array_screen(wrist_normal), 0, is_world=False)
            thumb_np = ema_func(to_numpy_array_screen(thumb_normal), 1, is_world=False)
            middle_np = ema_func(to_numpy_array_screen(middle_normal), 9, is_world=False)
            pinky_np = ema_func(to_numpy_array_screen(pinky_normal), 17, is_world=False)
            wrist_world_np = ema_func(to_numpy_array(wrist_world), 0)
            thumb_world_np = ema_func(to_numpy_array(thumb_world), 1)
            middle_world_np = ema_func(to_numpy_array(middle_world), 9)
            pinky_world_np = ema_func(to_numpy_array(pinky_world), 17)

            # 相対ベクトル(回転計算用)
            thumb_v = calc_relative_vector_ab(wrist_world_np, thumb_world_np)
            middle_v = calc_relative_vector_ab(wrist_world_np, middle_world_np)
            pinky_v = calc_relative_vector_ab(wrist_world_np, pinky_world_np)
            thumb_nv = calc_relative_vector_ab(wrist_np, thumb_np)
            pinky_nv = calc_relative_vector_ab(wrist_np, pinky_np)


            # 左右判定と法線ベクトル計算
            label = handedness.category_name # "Left" or "Right"
            if label == "Right":
                isRight = True
                palm_nv = calc_cross_np(thumb_v, pinky_v)
                palm_nv_screen = calc_cross_np(thumb_nv, pinky_nv)
            else:
                isRight = False
                palm_nv = calc_cross_np(pinky_v, thumb_v)
                palm_nv_screen = calc_cross_np(pinky_nv, thumb_nv)

            # 表示用の座標
            # to_pixel_coordinateにはnumpy配列
            wrist_pixel = to_pixel_coordinate(wrist_np)
            middle_pixel = to_pixel_coordinate(middle_np)
            palm_pos_np = palm_nv_screen * 10 + wrist_np
            # wristからの相対ベクトル(手のひらの法線ベクトル)
            palm_pixel = to_pixel_coordinate(palm_pos_np)

            # 左右判定の確認用
            if label == "Right":
                cv2.putText(image_bgr, "R", wrist_pixel, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                cv2.putText(image_bgr, "L", wrist_pixel, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # ベクトルの向き確認用
            cv2.arrowedLine(image_bgr, wrist_pixel, middle_pixel, (255, 0, 0), 3)
            cv2.arrowedLine(image_bgr, wrist_pixel, palm_pixel, (0, 255, 0), 3)
            

            # Unityが待っているデータ構造（JSON辞書）を作成
            data_dict = {
                "wristPos": wrist_np.tolist(),
                "palmNormal": palm_nv.tolist(),
                "middleVec": middle_v.tolist(),
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