using System.Net.Sockets;
using JetBrains.Annotations;
using UnityEngine;

public class TrackingManager : MonoBehaviour
{
    # region var-UDP
    [Header("UDPReceiver")]
    [SerializeField] GameObject receiver;
    #endregion

    #region var-Internal 
    UDPReceiver uDPReceiver;
    Vector3 swordInitPos;
    float scale = 0.01f;
    Transform _transform;
    #endregion
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        // スクリプトを取得
        uDPReceiver = receiver.GetComponent<UDPReceiver>();
        // 初期座標の記録
        swordInitPos = transform.position;
    }

    void Awake()
    {
        _transform = transform;
    }

    // Update is called once per frame
    void Update()
    {
        // 修正前: if(uDPReceiver.latestData != null && uDPReceiver.latestData.isRight)
        // ⬇️ 修正後:
        if (uDPReceiver.latestData != null && uDPReceiver.latestData.palmNormal != null && uDPReceiver.latestData.isRight)
        {
            // 差分計算
            Vector3 diff = uDPReceiver.latestData.WristPos - uDPReceiver.initWristPos;
            // x軸の反転修正
            // Tasks API移行に伴い、x軸の向きが一致したため、ここの反転処理（-1掛け）をコメントアウトします
            // diff.x *= -1;
            // 剣の初期座標に差分を足す
            transform.position = swordInitPos + diff * scale;
            // 回転角を計算
            Quaternion baseRot = Quaternion.LookRotation(uDPReceiver.latestData.MiddleVec, -uDPReceiver.latestData.PalmNormal);
            // Vector3 eulerAngle = baseRot.eulerAngles;
            // // オフセット
            // Quaternion offsetRot = Quaternion.Euler(0, 0, 120f);
            _transform.rotation = baseRot;
        }
    }
}
