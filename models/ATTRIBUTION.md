# Models

- `face_detection_yunet_2023mar.onnx` - YuNet face detector from the OpenCV Zoo (MIT licence),
  https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet . Used by `clipx/framing.py` to find
  streamer webcams so a crop can avoid them. Copied from the GTA-Auto-Clipper repo, which ships the same file under MIT.
- `person_yolox_s_2022nov.onnx` - YOLOX-S object detector (COCO, we use the 'person' class) from the OpenCV Zoo
  (Apache-2.0), https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox . Downloaded 2026-11-20
  (35.9 MB) and used by `clipx/tracking.py` to keep the player character inside a 9:16 crop.
