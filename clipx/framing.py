"""Smart framing helpers: find a streamer webcam (facecam) so a 9:16 crop can slide away from it, or so it can be blurred.

Idea borrowed from GTA-Auto-Clipper (it also uses the YuNet face model), re-implemented here:
  * a webcam face is SMALL, sits near an edge/corner, and stays put for the whole clip
  * faces of in-game characters are big, move, and sit in the middle -> they never count
"""
from pathlib import Path
import numpy as np
from .config import ROOT

MODEL = ROOT / "models" / "face_detection_yunet_2023mar.onnx"
_det = None


def _detector():
    global _det
    if _det is None:
        import cv2
        if not MODEL.exists():
            return None
        _det = cv2.FaceDetectorYN.create(str(MODEL), "", (320, 320), 0.8, 0.3, 5000)
    return _det


def sample_faces(video, t0, t1, n=9):
    """Face boxes (x, y, w, h in source pixels) for n frames spread over [t0, t1]. Returns (boxes_per_frame, W, H)."""
    import cv2
    det = _detector()
    cap = cv2.VideoCapture(str(video))
    if det is None or not cap.isOpened():
        return [], 0, 0
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = []
    try:
        for f in np.linspace(0.1, 0.9, n):
            cap.set(cv2.CAP_PROP_POS_MSEC, (t0 + (t1 - t0) * f) * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                out.append([])
                continue
            sc = min(320 / W, 320 / H)
            small = cv2.resize(frame, (round(W * sc), round(H * sc)), interpolation=cv2.INTER_AREA)
            canvas = np.zeros((320, 320, 3), np.uint8)
            px, py = (320 - small.shape[1]) // 2, (320 - small.shape[0]) // 2
            canvas[py:py + small.shape[0], px:px + small.shape[1]] = small
            _, faces = det.detect(canvas)
            boxes = []
            for fc in (faces if faces is not None else []):
                x, y, w, h = [float(v) for v in fc[:4]]
                boxes.append(((x - px) / sc, (y - py) / sc, w / sc, h / sc))
            out.append(boxes)
    finally:
        cap.release()
    return out, W, H


def pick_facecam(samples, W, H):
    """Pure logic (unit-tested). samples = list of per-frame face boxes. Returns an estimated webcam rectangle
    (x0, y0, x1, y1) in source pixels, or None when no persistent small edge face is found."""
    if W <= 0 or H <= 0 or not samples:
        return None
    small = []
    for boxes in samples:
        for (x, y, w, h) in boxes:
            cx, cy = x + w / 2, y + h / 2
            if 0 < w < W * 0.12 and 0 < h < H * 0.22 and (cx < W * 0.3 or cx > W * 0.7 or cy < H * 0.25 or cy > H * 0.75):
                small.append((cx, cy, w, h))
    need = max(3, int(np.ceil(len(samples) * 0.3)))
    if len(small) < need:
        return None
    cxs, cys = [s[0] for s in small], [s[1] for s in small]
    mx, my = float(np.median(cxs)), float(np.median(cys))
    if any(abs(x - mx) > W * 0.04 or abs(y - my) > H * 0.06 for x, y in zip(cxs, cys)):
        return None                       # moves around: not a fixed webcam
    mw = float(np.median([s[2] for s in small])) * 1.5
    mh = float(np.median([s[3] for s in small])) * 1.0
    return (max(0.0, mx - mw), max(0.0, my - mh), min(float(W), mx + mw), min(float(H), my + mh))


def facecam(video, t0, t1, n=9):
    samples, W, H = sample_faces(video, t0, t1, n)
    return pick_facecam(samples, W, H), W, H


def crop_cx_avoiding(cam, W, H, crop_w, preferred=0.5):
    """Pure logic. Crop window of crop_w pixels; cx in 0..1 (0 = left edge, 1 = right edge). Slide the window clear
    of the facecam rectangle when it overlaps. Returns (cx, clear: bool)."""
    avail = max(1.0, W - crop_w)
    left = preferred * avail
    if cam is None:
        return preferred, True
    x0, _, x1, _ = cam
    if x1 <= left or x0 >= left + crop_w:
        return preferred, True
    cam_c = (x0 + x1) / 2
    new_left = x1 + 4 if cam_c < left + crop_w / 2 else x0 - crop_w - 4
    new_left = min(avail, max(0.0, new_left))
    clear = new_left + crop_w <= x0 or new_left >= x1
    return new_left / avail, clear


def exposure_gamma(video, t0, t1, n=5, target=50.0, max_gamma=1.8):
    """Auto exposure: sample frames, and if the picture is dark return the ffmpeg eq gamma (>1 brightens) that lifts its
    average luma towards `target` (0..255). Returns 1.0 for normally exposed footage. Pure maths in lift_gamma()."""
    import cv2
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return 1.0
    means = []
    try:
        for f in np.linspace(0.1, 0.9, n):
            cap.set(cv2.CAP_PROP_POS_MSEC, (t0 + (t1 - t0) * f) * 1000)
            ok, fr = cap.read()
            if ok and fr is not None:
                g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
                h, w = g.shape
                means.append(float(g[int(h * 0.1):int(h * 0.8), int(w * 0.1):int(w * 0.9)].mean()))
    finally:
        cap.release()
    return lift_gamma(float(np.median(means)) if means else target, target, max_gamma)


def lift_gamma(mean_luma, target=50.0, max_gamma=1.8):
    """Pure logic (unit-tested): gamma that maps `mean_luma` to `target`; never darkens, capped so noise stays sane."""
    import math
    if mean_luma >= target * 0.8 or mean_luma <= 0:
        return 1.0
    g = math.log(max(mean_luma, 1.0) / 255.0) / math.log(target / 255.0)
    return round(min(max_gamma, max(1.0, g)), 3)
