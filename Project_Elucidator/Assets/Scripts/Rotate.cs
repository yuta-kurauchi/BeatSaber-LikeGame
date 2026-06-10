using UnityEngine;

public class Rotate : MonoBehaviour
{
    [ContextMenu("HandAnchorに手をあわせる")]
    public void Rotation1()
    {
        transform.localRotation = Quaternion.AngleAxis(90f, new Vector3(0, 1, 0));
    }
}
