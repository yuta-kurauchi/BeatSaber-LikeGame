# 学習内容の整理

---

## lock(lockObj) とは?
- 複数スレッドから変数にアクセスしようとしているときに、同時にアクセスできないようにするためのもの。
- lockObjという鍵で管理している。

## Quaternion.LookRotation
- 公式リファレンス
    指定された forward と upwards 方向に回転します
- この意味
    - `forward`（第一引数） ➔ 「オブジェクトのローカルZ軸（青色の矢印）をどの方向に向けたいか」
    - `upwards`（第二引数） ➔ 「オブジェクトのローカルY軸（緑色の矢印）をどの方向に向けたいか」

## Awake関数
- スクリプトのインスタンスがロードされたときに呼び出される。
- オブジェクトのインスタンス生成後に呼び出される。
- オブジェクトの参照を安全に行える。
- コンポーネントを参照しておくことで、Update関数でなんども使うコンポーネントの参照などをしておく。
```cs
// Awakeでの処理
void Awake() {
    _transform = transform;
}

void Update() {
    _transform.position = Vectoer3;
}
```

## EndPoint とは？
- IPとポートのセット
```cs
// どのIP,どのポート番号でも受け取る。
IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);
```
- ポートは0でどこでも可という意味

## 同期処理
- その処置が終わるまで次に進めない。
- 別スレッドを使う。

---

## PythonController.cs

### namespace
System.Diagnostics : OSのプロセス用のクラスなど
System.IO : ファイルシステム用のクラスなど

### パスの構築
```CS
void Start()
    {
        // Application.dataPath は「Project_Elucidator/Assets」を指す
        string scriptPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking", "hand_tracking_.py"));
    }
```
`Path.GetFullPath` : 絶対パスを生成
`Path.Combine` : パスをOSのルール(Windowsなら`\`,Macなら`/`)に合わせて繋ぐ

```CS
string pythonExePath = "";
#if UNITY_EDITOR_WIN
        pythonExePath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking/venv/Scripts/python.exe"));
#else
        string macPath1 = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking/venv/bin/python3"));
        string macPath2 = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking/venv/bin/python"));
        pythonExePath = File.Exists(macPath1) ? macPath1 : macPath2;
#endif
```
条件付きコンパイル(プリプロセッサディレクティブ)
OSによって違うパスをそれぞれに合わせて代入できるようにしている。

`? :`これは三項演算子というもので、macPath1があればそれで、なければmacPath2を代入
```
(条件)　? (trueの場合の値) : (falseの場合の値)
```

### 実行と終了

```CS
ProcessStartInfo startInfo = new ProcessStartInfo();
startInfo.FileName = pythonExePath;
startInfo.Arguments = $"\"{scriptPath}\"";
startInfo.UseShellExecute = false;
startInfo.CreateNoWindow = true;

// カレントディレクトリをスクリプトの場所に固定する（.taskファイルを読み込めるようにするため）
startInfo.WorkingDirectory = Path.GetDirectoryName(scriptPath);

pythonProcess = Process.Start(startInfo); //実行
```

`ProcessStartInfo` : これはプロセスを起動するための情報を入力するための型
- **ここがゲームでは重要**
`UseShellExecute` = false : シェルを経由せず、直接実行可能ファイル（.exe）を起動。 
`CreateNoWindow =ture` : コンソールを表示させない
実行のたびにいちいちターミナルなどのウィンドウが出ないようにする。
こういった設定をしておくことで、ゲームが中断されずに済む

`WorkingDirectory` : スクリプトのパスをワークディレクトリに指定することで、pythonでパスを使う処理(tasksとか)も問題なく行える。

```CS
pythonProcess.Kill();
pythonProcess.Dispose();
UnityEngine.Debug.Log("[Python] トラッキングプロセスを正常に終了しました。");
```
`OnDestroy` : 再生停止時やシーン遷移時に自度で呼ばれる
`kill` : プロセスを強制終了させる

### スレッド(Thread)とプロセス(process)の違い
- スレッド(Thread) 
    1つのプログラムの中で同時に処理するためのもの。並列処理
- プロセス(Process)
    完全に別のプログラム

### 最終的なビルド時のこのファイル(バックエンド)の扱い
`PyInstaller` : これで、pythonのソースコードと、mediapipeなどのライブラリを一つの実行ファイルにする。
それをUnityの`StreamingAssets`という特別なフォルダに入れることで、Unityのビルド時に同封してくれる。

---

## OpenCV
- 矢印の書き方
```python
cv2.arrowedLine(画像, 始点の座標, 終点の座標, 色(B, G, R), 線の太さ)
```
- キャストの必要性
座標を示すときに、入れるのはピクセル座標である。
そのピクセル座標に変換するときに、
正規化座標 * heightとかで実装していたので、floatになってしまい以下のようなエラーが出た。
```
cv2.error: OpenCV(4.13.0) :-1: error: (-5:Bad argument) in function 'putText'
```
必ずキャストしてintに直してから入れるようにすべき