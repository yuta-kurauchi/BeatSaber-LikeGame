using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using System.Collections.Generic;


public class UDPReceiver : MonoBehaviour
{

    #region var-Setting
    [Header("UDP Setting")]
    public int port = 50001;
    [Header("Debug")] 
    public bool showDebugLog = true;
    #endregion

    #region var_Internal
    UdpClient udpClient;
    Thread receiveThread;
    bool isReceiving = false;
    int receiveCount = 0;
    // ロック用
    private readonly object lockObj = new object();
    #endregion

    #region var-External
    public TrackingData latestData, tempData;
    public System.Action<TrackingData> OnDataReceived;
    public Vector3 initWristPos;
    #endregion

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        // 受信するまでnull
        latestData = null;
        StartReceiving();
    }

    // Update is called once per frame
    void Update()
    {
        lock(lockObj)
        {
            if(latestData != null)
            {
                Debug.Log(latestData.PalmNormal);
            }
        }
    }

    #region
    void StartReceiving()
    {
        try
        {
            // ポート番号を指定して受信用のsocketをインスタンス化
            udpClient = new UdpClient(port);
            isReceiving = true;

            // ReceiveDataという名前で新しいスレッドを作成
            receiveThread = new Thread(ReceiveData);
            receiveThread.IsBackground = true;
            receiveThread.Start(); // スレッドを開始

            Debug.Log($"UDP受信開始: Port {port}");
        }
        catch (Exception e)
        {
            // エラーメッセージ
            Debug.Log($"UDP受信開始エラー: {e.Message}");
        }
    }
    #endregion

    #region ReceiveDataThread
    void ReceiveData()
    {
        // どのIPadress、どのport番号からでも受信できるようにEndPointを初期化
        // EndPointってなんやねん
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);

        while (isReceiving)
        {
            try
            {
                // データの受信、バイト型の配列としてdataに受け取る。
                // remoteEndPointをrefで渡すことで、送信元を取得?
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                // dataをjson形式に戻す
                string jsonString = Encoding.UTF8.GetString(data);
                /*更新中は外部からの操作(読み取りとか)を受け付けない。*/
                
                // json形式をTrackingData classに変換
                tempData = JsonConvert.DeserializeObject<TrackingData>(jsonString);

                if(receiveCount == 0)
                {
                    receiveCount = 1;
                    initWristPos.z = tempData.WristPos.z;
                    initWristPos.x = 320;
                    initWristPos.y = -240;
                }

                lock(lockObj)
                {
                    latestData = tempData;
                }
            }
            catch (Exception e)
            {
                // エラーメッセージ
                Debug.Log($"UDP受信エラー: {e.Message}");
            }
        }
    }
    #endregion

    #region OnDestroy
    // 終了時
    void OnDestroy()
    {
        EndReceiving();
    }
    #endregion

    #region EndReceiving
    // 終了処理
    void EndReceiving()
    {
        isReceiving = false;
        udpClient.Close();
    }
    #endregion
}

[Serializable]
public class TrackingData
{
    // 手首の座標
    [JsonProperty("wristPos")]
    public List<float> wristPos;
    [JsonIgnore]
    // 読み取り時だけ変換(getterとかいうやつ?)
    public Vector3 WristPos => new Vector3(wristPos[0], wristPos[1], wristPos[2]);
    // 法線
    [JsonProperty("palmNormal")]
    public List<float> palmNormal;
    [JsonIgnore]
    public Vector3 PalmNormal => new Vector3(-palmNormal[0], palmNormal[1], palmNormal[2]);
    // 中指へのベクトル
    [JsonProperty("middleVec")]
    public List<float> middleVec;
    [JsonIgnore]
    public Vector3 MiddleVec => new Vector3(-middleVec[0], middleVec[1], middleVec[2]);
    // 右手かどうかのラベル
    [JsonProperty("isRight")]
    public bool isRight;
}