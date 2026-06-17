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