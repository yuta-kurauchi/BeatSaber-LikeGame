import cv2
import mediapipe as mp
import numpy as np
import socket
import json

# 通信用
UNITY_HOST = "127.0.0.1" # 自分のパソコンを指定
UNITY_PORT = 50001 # 任意のポート番号
udp_sock = None # グローバルに宣言

# ソケットの初期化
def init_udp_socket():
    global udp_sock # 変更を加えるためグローバル宣言
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP ソケットとしてインスタンス化
        print(f"UDP通信を初期化しました。({UNITY_HOST}/{UNITY_PORT})")
        return True
    except Exception as e:
        print(f"UDP初期化失敗: {e}") # 初期化失敗の通知と原因
        return False

def send_to_unity(message):
    if not udp_sock:
        return False
    
    try:
        json_message = json.dumps(message) # 辞書をjson形式に変換
        udp_sock.sendto(json_message.encode('utf-8'), (UNITY_HOST, UNITY_PORT)) # utf-8で符号化して送信
        return True
    except Exception as e:
        print(f"UDP送信エラー: {e}") # 送信失敗の通知と原因
        return False

# EMA用
alpha = 0.2
smoothed_vector = {0:None, 1:None, 9:None, 17:None}
Smoothed_vector = {0:None}

# numpy配列に変換してEMA
def to_np(lm, id):
    raw_vector =  np.array([lm.x, lm.y, lm.z])
    if smoothed_vector[id] is None:
        smoothed_vector[id] = raw_vector
    else:
        smoothed_vector[id] = alpha * raw_vector + (1 - alpha) * smoothed_vector[id]
    return smoothed_vector[id]

# notWorld用
def To_np(lm, id):
    raw_vector =  np.array([lm.x, lm.y, lm.z])
    if Smoothed_vector[id] is None:
        Smoothed_vector[id] = raw_vector
    else:
        Smoothed_vector[id] = alpha * raw_vector + (1 - alpha) * Smoothed_vector[id]
    return Smoothed_vector[id]

# スケーリング
def scale(Pos_np, h, w):
    scale_np = Pos_np.copy()
    scale_np[0] *= w
    scale_np[1] *= -h # 反転解除とスケーリング
    return scale_np

def to_list(np_vector):
    return np_vector.tolist()

def reSetVector():
    smoothed_vector[0] = None
    smoothed_vector[1] = None
    smoothed_vector[9] = None
    smoothed_vector[17] = None
    Smoothed_vector[0] = None

# 手首からの相対座標に変換
def calc_v(id, landmarks, w_np):
    np_array = to_np(landmarks[id], id)
    vector = np_array - w_np
    # y軸反転
    vector[1] *= -1
    return vector

def calc_nv(va, vb):
    return np.cross(va, vb)

def putText(palm_nv):
    text_up = 'Up'
    text_down = 'Down'
    org = (100, 200) # 挿入座標
    fontFace = cv2.FONT_HERSHEY_SIMPLEX 
    fontScale = 3
    color = (255, 255, 255) # 白
    thickness = 2 # 線の太さ
    lineType = cv2.LINE_AA # 線のタイプ、アルゴリズム
    if palm_nv[1] > 0:
        cv2.putText(image, text_up, org, fontFace, fontScale, color, thickness, lineType)
    else:
        cv2.putText(image, text_down, org, fontFace, fontScale, color, thickness, lineType)

# MediaPipe    
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
# 描画設定
mesh_drawing_spec = mp_drawing.DrawingSpec(thickness = 2, color = (0, 255, 0)) # 線を緑で表示
mark_drawing_spec = mp_drawing.DrawingSpec(thickness = 2, circle_radius = 1, color = (0, 0, 255)) # 赤の点でランドマークを表示

# カメラの読み込み(0番を指定)
cap = cv2.VideoCapture(0)

# ソケットのインスタンス化
init_udp_socket()

# MediaPipeの手の検出設定
with mp_hands.Hands(
        max_num_hands = 1, #片手だけを検出
        min_detection_confidence = 0.5,
        static_image_mode = False) as hands:

    # カメラがついている間
    while cap.isOpened():
        #戻り値を同時に代入しているだけ
        success, frame = cap.read()
        if not success:
            continue

        # MediaPipeはRGB形式を扱うので、OpenCVのBGR形式から変換
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # 左右反転を修正
        image = cv2.flip(image, 1)
        height = image.shape[0]
        width = image.shape[1]

        # 検出を実行
        results = hands.process(image)
        # 映像をBGRに戻して描画の準備, 描画はopencvで行うのでBGRに戻す。
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 手が検出された場合、関節を描画する
        # results.multi_hand_landmarksに21箇所の座標が入っている
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            for i in range(num_hands):
                hand_landmarks = results.multi_hand_landmarks[i]
                hand_wlandmarks = results.multi_hand_world_landmarks[i]
                #手首のnumpy配列を取得
                wrist_np = to_np(hand_wlandmarks.landmark[0], 0)
                wrist_np_notWorld = To_np(hand_landmarks.landmark[0], 0)
                #手首の座標をリアルスケールで計算
                wristPos_rial = scale(wrist_np_notWorld, height, width)
                # 手首からの相対座標(ベクトル)を計算
                thumb_v = calc_v(1, hand_wlandmarks.landmark, wrist_np)
                middleF_v = calc_v(9, hand_wlandmarks.landmark, wrist_np)
                pinky_v = calc_v(17, hand_wlandmarks.landmark, wrist_np)
                # 右手か左手かの判定
                if results.multi_handedness:
                    handedness = results.multi_handedness[i]
                    # 手のラベルを取得(Lef or Right)
                    label = handedness.classification[0].label
                    if label == "Right":
                        isRight = True
                        # 掌の法線ベクトル(右手想定)
                        palm_nv = calc_nv(thumb_v, pinky_v)
                    else:
                        isRight = False
                        # 掌の法線ベクトル(左手想定)
                        palm_nv = calc_nv(pinky_v, thumb_v)
                    # テキストの挿入　
                    putText(palm_nv)
                # 21箇所の関節とそれらを結ぶ線を描画
                mp_drawing.draw_landmarks(
                        image = image,
                        landmark_list = hand_landmarks,
                        connections = mp_hands.HAND_CONNECTIONS,
                        landmark_drawing_spec = mark_drawing_spec,
                        connection_drawing_spec = mesh_drawing_spec)
                # データ(辞書)
                data_dict = {
                "wristPos" : to_list(wristPos_rial),
                "palmNormal" : to_list(palm_nv),
                "middleVec" : to_list(middleF_v),
                "isRight" : isRight}

                # データの送信
                send_to_unity(data_dict)

        # 手の検出がされなかった場合。
        else:
            # 一つ前の座標をリセット
            reSetVector()

        # ウィンドウに表示
        cv2.imshow('MediaPipe Hand Tracking', image)

        # ESCでウィンドウを閉じる
        if cv2.waitKey(5) & 0xFF == 27:
            break

# ソケットを閉じる
udp_sock.close()
# カメラをリリース
cap.release()
# 出力しているウィンドウをすべて閉じる
cv2.destroyAllWindows()