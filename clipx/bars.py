"""Detect baked-in black bars (letterbox/pillarbox) so they can be cropped away."""
import re
import subprocess


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def detect(path, iw, ih):
    """Returns (w, h, x, y) of the real picture. Samples a few short windows (decoding a whole 4K file is very slow)
    and takes the union of what it finds, so dark scenes don't fool it."""
    d = _dur(path)
    starts = [0.0] if d < 60 else [d * f for f in (0.05, 0.2, 0.4, 0.6, 0.8)]
    boxes = []
    for s in starts:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{s:.1f}", "-t", "6", "-i", str(path),
                            "-vf", "fps=2,cropdetect=limit=24:round=2:reset=0", "-f", "null", "-"],
                           capture_output=True, text=True)
        m = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", p.stderr)
        if m:
            boxes.append(tuple(map(int, m[-1])))
    if not boxes:
        return iw, ih, 0, 0
    x0 = min(b[2] for b in boxes); y0 = min(b[3] for b in boxes)
    x1 = max(b[2] + b[0] for b in boxes); y1 = max(b[3] + b[1] for b in boxes)
    w, h, x, y = x1 - x0, y1 - y0, x0, y0
    if w < iw * 0.5 or h < ih * 0.5 or (iw - w < 8 and ih - h < 8):
        return iw, ih, 0, 0
    return w, h, x, y
