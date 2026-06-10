using UnityEngine;
using System.Diagnostics;
using System.IO;
using System;

public class PythonController : MonoBehaviour
{
    private Process pythonProcess;

    void Start()
    {
        // 1. スクリプトのファイル名を実際のファイル名（hand_tracking_.py）に確実に合わせる
        // Application.dataPath は「Project_Elucidator/Assets」を指すため、
        // そこから2階層上がって「BeatSaber-LikeGame」に出てから「python-tracking」に入ります。
        string scriptPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking", "hand_tracking_.py"));

        string pythonExePath = "";
        #if UNITY_EDITOR_WIN
                pythonExePath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking/venv/Scripts/python.exe"));
        #else
                string macPath1 = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking/venv/bin/python3"));
                string macPath2 = Path.GetFullPath(Path.Combine(Application.dataPath, "../../python-tracking/venv/bin/python"));
                pythonExePath = File.Exists(macPath1) ? macPath1 : macPath2;
        #endif

        // パスのデバッグログ（正しく計算できているか確認用）
        UnityEngine.Debug.Log($"[Python] 実行ファイルパス: {pythonExePath}");
        UnityEngine.Debug.Log($"[Python] スクリプトパス: {scriptPath}");

        if (!File.Exists(pythonExePath))
        {
            UnityEngine.Debug.LogError($"[Python] 指定された場所に python.exe が見つかりません: {pythonExePath}");
            return;
        }

        if (!File.Exists(scriptPath))
        {
            UnityEngine.Debug.LogError($"[Python] 指定された場所に スクリプト が見つかりません: {scriptPath}");
            return;
        }

        try
        {
            ProcessStartInfo startInfo = new ProcessStartInfo();
            startInfo.FileName = pythonExePath;
            startInfo.Arguments = $"\"{scriptPath}\"";
            startInfo.UseShellExecute = false;
            startInfo.CreateNoWindow = true;
            
            // 【重要】カレントディレクトリをスクリプトの場所に固定する（.taskファイルを読み込めるようにするため）
            startInfo.WorkingDirectory = Path.GetDirectoryName(scriptPath);

            UnityEngine.Debug.Log("[Python] UnityからPythonトラッキングプロセスを起動します...");
            pythonProcess = Process.Start(startInfo);
        }
        catch (Exception e)
        {
            UnityEngine.Debug.LogError($"[Python] プロセスの起動に失敗しました: {e.Message}");
        }
    }

    void OnDestroy()
    {
        if (pythonProcess != null && !pythonProcess.HasExited)
        {
            try
            {
                pythonProcess.Kill();
                pythonProcess.Dispose();
                UnityEngine.Debug.Log("[Python] トラッキングプロセスを正常に終了しました。");
            }
            catch (Exception e)
            {
                UnityEngine.Debug.LogWarning($"[Python] プロセス終了時に例外が発生しました: {e.Message}");
            }
        }
    }
}