# BeatSaber-LikeGame⚔️
### ⚠️ 開発中 ⚠️

リアルタイム・ハンドトラッキング技術を融合させた、マルチプラットフォーム対応予定の3Dアクションゲーム（BeatSaber-Like Hand Game）のプロトタイプ基盤リポジトリです。

AI 骨格認識エンジン **MediaPipe Tasks API** をスタンドアロンプロセスとして裏で動作させ、Unity 6 とUDP通信を行うことで、プレイヤーの手の動きをゲーム内のオブジェクトへ同期させます。

---

## 🛠 プロジェクト構造 (Repository Structure)

本リポジトリは、環境のポータビリティ（持ち運びやすさ）を高めるため、フロント（Unity）とAI認識バックエンド（Python）がセパレートされた並列構造を採用しています。

```text
BeatSaber-LikeGame/
│
├── .gitignore               # Unity-tmplate pythonの仮想環境やmediapipeのモデルを追加
├── README.md                # 本ドキュメント
│
├── python-tracking/         # AIハンドトラッキング・バックエンド
│   ├── hand_landmarker.task # MediaPipe最新の学習済みモデルアセット
│   ├── hand_tracking_.py    # Tasks APIベースのトラッキング＆UDP送信スクリプト
│   ├── requirements.txt     # 依存ライブラリ一覧 (OpenCV, numpy, mediapipe)
│   └── venv/                # Pythonローカル仮想環境フォルダ（Git非追跡）
│
└── Project_Elucidator/      # Unityゲームプロジェクト (Unity 6 URP)
    ├── Assets/
    │   ├── Scripts/
    │   │   ├── PythonController.cs # Unityの起動・停止にPythonを連動させるラッパー
    │   │   ├── UDPReceiver.cs      # バックグラウンドスレッドでのJSONデシリアライズ
    │   │   └── TrackingManager.cs  # Quaternionを用いた3Dオブジェクトの座標・回転同期
    │   └── Scenes/
    │       ├── TitleScene.unity    # メインタイトル画面（未着手）
    |       ├── GameScene.unity     # ゲーム本編用(未着手)
    │       └── SampleScene.unity   # トラッキング検証用シーン
    └── ProjectSettings/
```
---

## 🚀 クイックスタート (Mac / Windows)
1. Python バックエンドの環境復元
まずは python-tracking フォルダに移動し、お使いの環境に依存しない独立した仮想環境を構築します。
```Bash
cd python-tracking

# 1. 仮想環境（venv）の作成
python -m venv venv

# 2. 仮想環境のアクティベート
# Windows (PowerShellの場合):
.\venv\Scripts\activate
# Mac / Linux:
source venv/bin/activate

# 3. 依存パッケージのインストール
pip install -r requirements.txt
```
2. AI モデルファイルの配置
GoogleのMediaPipe公式リポジトリから、最新の手の骨格検出用モデルファイルをダウンロードし、`python-tracking/`フォルダの直下に配置してください。
- ファイル名: `hand_landmarker.task`
- [Hand landmarks detection guide]("https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker#models") -> Models
Models -> HandLandmarker (full)からダウンロード
3. Unityの起動と実行
    1. Unity Hub から `Project_Elucidator` フォルダを Unity Editor（バージョン: 6000.3.9f1）で開きます。
    2. Assets/Scenes/SampleScene を開きます。
    3. Unityエディタ上部の 再生（▶）ボタン を押します。
    【自動化仕様】
    Unityを再生すると、`PythonController.cs` が自動的に裏で `venv` のPython環境および `hand_tracking_.py` を立ち上げ、Webカメラを起動します。手動でターミナルを操作する必要はありません。Unityの停止（■）ボタンを押すと、裏のPythonプロセスも自動で安全に終了します。

---

## 📡 通信データ仕様 (UDP JSON Payload)
```JSON
{
  "wristPos": [0.0, 0.0, 0.0],    // 手首の正規化スクリーン座標 (X, Y, Z)
  "palmNormal": [0.0, 0.0, 0.0],  // 掌の法線ベクトル（手の向き・傾き計算用）
  "middleVec": [0.0, 0.0, 0.0],   // 手首から中指へのベクトル（手の回転方向計算用）
  "isRight": true                 // 右手判定: true / 左手判定: false
}
```
Unity側では、`Quaternion.LookRotation(middleVec, -palmNormal)`を用いて、3Dモデルの正確な三次元回転角度を毎フレーム同期させています。
