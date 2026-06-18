using UnityEngine;

public class TrackingManager : MonoBehaviour
{
    # region var-UDP
    [Header("UDPReceiver")]
    [SerializeField] GameObject receiver;
    #endregion

    #region var-Internal 
    UDPReceiver uDPReceiver;
    TrackingData handData;
    Transform _transform;
    Camera _mainCamera;
    #endregion
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        // スクリプトを取得
        uDPReceiver = receiver.GetComponent<UDPReceiver>();
        // メインカメラの取得
        _mainCamera = Camera.main;
    }

    void Awake()
    {
        _transform = transform;
    }

    // Update is called once per frame
    void Update()
    {
        // Debug.Log("handdataがnullです");
        // 窓口経由で最新のデータをコピー
        handData = uDPReceiver.GetLatestData();
        if (handData != null && handData.isRight)
        {
            Vector3 viewportPos = handData.WristPos;
            // zだけ変更,zがカメラからの距離を表す。
            viewportPos.z = 2.0f;
            _transform.position = _mainCamera.ViewportToWorldPoint(viewportPos);
            // 回転角を計算
            Quaternion baseRot = Quaternion.LookRotation(handData.MiddleVec, handData.PalmNormal);
            _transform.rotation = baseRot;
        }
    }
}
