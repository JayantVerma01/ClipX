"""Follow the player character so a 9:16 crop keeps them in frame (idea from GTA-Auto-Clipper, own implementation).

GTA's third-person camera does not keep the character in the middle (over-the-shoulder, aiming, vehicles), and a 9:16 crop
shows only ~32% of a 16:9 frame, so a fixed crop often loses the player. We detect people with YOLOX-S (OpenCV Zoo,
Apache-2.0, models/person_yolox_s_2022nov.onnx), pick the player, smooth the path and return keyframes for a panning crop.
When no clear player is found (driving, cutscenes, aerial shots) it returns None and the caller keeps its static crop.
"""
import math
from pathlib import Path
import numpy as np
from .config import ROOT

MODEL = ROOT / "models" / "person_yolox_s_2022nov.onnx"
_session = None
_grid = None


def available():
    return MODEL.exists()


def _sess():
    global _session
    if _session is None:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        _session = ort.InferenceSession(str(MODEL), opts, providers=["CPUExecutionProvider"])
    return _session


def _make_grid():
    rows = []
    for stride in (8, 16, 32):
        n = 640 // stride
        ys, xs = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        rows.append(np.stack([xs.ravel(), ys.ravel(), np.full(n * n, stride)], axis=1))
    return np.concatenate(rows).astype(np.float32)


def detect_people(frame, conf=0.35):
    """Person boxes (x, y, w, h, score) in frame pixels. YOLOX output = (8400, 85): xywh, objectness, 80 class scores."""
    import cv2
    global _grid
    if _grid is None:
        _grid = _make_grid()
    h, w = frame.shape[:2]
    r = min(640 / w, 640 / h)
    img = np.full((640, 640, 3), 114, dtype=np.uint8)
    img[:round(h * r), :round(w * r)] = cv2.resize(frame, (round(w * r), round(h * r)))
    out = _sess().run(None, {"images": img.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    xy = (out[:, :2] + _grid[:, :2]) * _grid[:, 2:3]
    wh = np.exp(out[:, 2:4]) * _grid[:, 2:3]
    score = out[:, 4] * out[:, 5]                 # objectness * P(person)
    keep = score > conf
    if not keep.any():
        return []
    xy, wh, score = xy[keep] / r, wh[keep] / r, score[keep]
    boxes = [[float(x - bw / 2), float(y - bh / 2), float(bw), float(bh)] for (x, y), (bw, bh) in zip(xy, wh)]
    idx = cv2.dnn.NMSBoxes(boxes, score.tolist(), conf, 0.45)
    return [(*boxes[i], float(score[i])) for i in np.array(idx).ravel()]


def pick_player(people, fw, fh, prev_x=None):
    """Pure logic (unit-tested). The player = a large person in the lower-middle of the screen, close to the previous pick.
    Far-away pedestrians (small) and people at the very edges are ignored. Returns centre x as a fraction, or None."""
    best, best_cost = None, None
    for x, y, w, h, s in people:
        if h < fh * 0.12:
            continue
        cx, cy = (x + w / 2) / fw, (y + h / 2) / fh
        if cx < 0.12 or cx > 0.88:
            continue
        cost = abs(cx - 0.45) * 1.2 + abs(cy - 0.6) * 0.6 - (h / fh) * 1.5
        if prev_x is not None:
            cost += abs(cx - prev_x) * 1.5
        if best_cost is None or cost < best_cost:
            best, best_cost = cx, cost
    return best


def smooth_path(times, xs, default=0.5, max_speed=0.12):
    """Pure logic (unit-tested). Fill gaps by holding the last position, 3-point median (kills one-frame jumps to another
    person), then a speed limit (fraction of frame width per second) so the pan never whips."""
    filled, last = [], None
    for x in xs:
        if x is None:
            x = last
        filled.append(x)
        if x is not None:
            last = x
    first = next((x for x in filled if x is not None), default)
    filled = [first if x is None else x for x in filled]
    med = [float(np.median(filled[max(0, i - 1):i + 2])) for i in range(len(filled))]
    out = [med[0]]
    for i in range(1, len(med)):
        dt = max(1e-3, times[i] - times[i - 1])
        step = max(-max_speed * dt, min(max_speed * dt, med[i] - out[-1]))
        out.append(out[-1] + step)
    return out


def track(video, t0, t1, fps=2.0):
    """Keyframes [(t_from_t0, centre_x_fraction)] for the player over [t0, t1], or None if there is no clear player."""
    if not available():
        return None
    import cv2
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    fw, fh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fw <= 0 or fh <= 0 or fw / fh < 1.2:
        cap.release()
        return None
    times, xs, prev = [], [], None
    try:
        n = max(2, int((t1 - t0) * fps) + 1)
        for i in range(n):
            t = min(t1 - t0, i / fps)
            cap.set(cv2.CAP_PROP_POS_MSEC, (t0 + t) * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            x = pick_player(detect_people(frame), fw, fh, prev)
            if x is not None:
                prev = x
            times.append(t)
            xs.append(x)
    finally:
        cap.release()
    if not times or sum(x is not None for x in xs) < max(2, len(xs) // 4):
        return None                                 # no clear player (driving / cutscene / aerial): keep the static crop
    return list(zip(times, smooth_path(times, xs)))


def left_expr(keys, crop_w, frame_w, speed=1.0):
    """ffmpeg expression for the crop's left edge in SOURCE pixels (piecewise-linear pan through the keyframes).
    `t` in a crop filter is the piece-local time after any slow-motion, so key times are divided by `speed`."""
    def at(c):
        left = min(max(c * frame_w - crop_w / 2, 0.0), frame_w - crop_w)
        return f"{left:.1f}"
    ks = [(t / speed, c) for t, c in keys]
    if len(ks) == 1:
        return at(ks[0][1])
    expr = at(ks[-1][1])
    for (t0, c0), (t1, c1) in reversed(list(zip(ks, ks[1:]))):
        if t1 <= t0:
            continue
        seg = f"({at(c0)}+({at(c1)}-{at(c0)})*(t-{t0:.2f})/{t1 - t0:.2f})"
        expr = f"if(lt(t\\,{t1:.2f})\\,{seg}\\,{expr})"
    return expr
