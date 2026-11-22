import os
import sys
import urllib.request
URL = "https://github.com/opencv/opencv_zoo/raw/main/models/object_detection_yolox/object_detection_yolox_2022nov.onnx"
DST = "models/person_yolox_s_2022nov.onnx"
os.makedirs("models", exist_ok=True)
tmp = DST + ".part"
req = urllib.request.Request(URL, headers={"User-Agent": "clipx-model-fetch"})
with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
    total = 0
    while True:
        b = r.read(1 << 20)
        if not b:
            break
        f.write(b)
        total += len(b)
print("downloaded bytes:", total)
if total < 5_000_000:
    os.remove(tmp)
    sys.exit("download too small - refusing to keep it")
os.replace(tmp, DST)
import onnxruntime as ort
s = ort.InferenceSession(DST, providers=["CPUExecutionProvider"])
print("loads OK. inputs:", [(i.name, i.shape) for i in s.get_inputs()], "outputs:", [(o.name, o.shape) for o in s.get_outputs()])
