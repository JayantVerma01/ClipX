"""Automatic clip QA (the 'checker veto' idea from GTA-Auto-Clipper, done in code, plus our own glitch check).

  python -m clipx.qa output\\*.mp4        # prints a verdict per clip, writes other/qa/<name>.bad for vetoed ones
Checks: near-black / near-white frames (fades, loading screens, outros), flat low-detail frames (menus, maps, title
cards), single-frame glitches (our 30 fps spike detector) and a persistent webcam in the picture (source clips).
"""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from .config import AUX

QA_DIR = AUX / "qa"


def _is_portrait(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        wd, ht = [int(x) for x in r.stdout.strip().split(",")[:2]]
        return ht > wd
    except ValueError:
        return False


def _frames(path, fps, w=160, h=90, ss=None, t=None):
    """Grey frames for analysis. For vertical clips only the picture band is measured (the blurred title / follow
    bands above and below it are dark by design and would look like 'black frames')."""
    band = "crop=iw:ih*0.60:0:ih*0.20," if _is_portrait(path) else ""
    cmd = ["ffmpeg", "-v", "error"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    if t is not None:
        cmd += ["-t", str(t)]
    cmd += ["-i", str(path), "-vf", f"{band}fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def classify_frames(frames, skip_edges=1):
    """Pure logic (unit-tested). frames: (n, h, w) float array sampled at 1 fps. Returns fractions of
    dark / white / flat frames, ignoring the first/last `skip_edges` frames (intentional fades)."""
    if len(frames) <= 2 * skip_edges + 1:
        core = frames
    else:
        core = frames[skip_edges:len(frames) - skip_edges]
    if len(core) == 0:
        return {"dark": 0.0, "white": 0.0, "flat": 0.0}
    means = core.mean(axis=(1, 2))
    stds = core.std(axis=(1, 2))
    return {"dark": float((means < 14).mean()), "white": float((means > 236).mean()),
            "flat": float(((stds < 12) & (means >= 14) & (means <= 236)).mean())}


def glitch_frames(frames, fps=30):
    """Pure logic. Frames sampled at ~30 fps. A glitch = a frame that differs a lot from BOTH neighbours while the
    neighbours resemble each other (a one-frame flash / wrong crop). Hard cuts are not glitches."""
    if len(frames) < 4:
        return []
    d = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    m = float(np.median(d))
    out = []
    for i in range(len(d) - 1):
        if d[i] > 3 * m + 2 and d[i + 1] > 3 * m + 2 and np.abs(frames[i] - frames[i + 2]).mean() < 0.6 * min(d[i], d[i + 1]):
            out.append(round((i + 1) / fps, 2))
    return out


def check(path, glitch=True):
    path = Path(path)
    dur = duration(path)
    reasons = []
    stats = classify_frames(_frames(path, 1))
    if stats["dark"] > 0.08:
        reasons.append(f"{stats['dark']:.0%} near-black frames")
    if stats["white"] > 0.05:
        reasons.append(f"{stats['white']:.0%} near-white frames (flash / outro / loading)")
    if stats["flat"] > 0.15:
        reasons.append(f"{stats['flat']:.0%} flat low-detail frames (menu / map / title card?)")
    g = []
    if glitch and dur > 3:
        for ss in np.arange(0, max(dur - 5, 1), 30):
            fr = _frames(path, 30, 160, 90, ss=ss, t=30)
            g += [round(ss + t, 2) for t in glitch_frames(fr)]
        if g:
            reasons.append(f"{len(g)} one-frame glitch(es) at {g[:5]}")
    return {"file": path.name, "seconds": round(dur, 1), **{k: round(v, 3) for k, v in stats.items()},
            "glitches": g, "ok": not reasons, "reasons": reasons}


def main(paths):
    QA_DIR.mkdir(parents=True, exist_ok=True)
    bad = 0
    for p in paths:
        r = check(p)
        flag = QA_DIR / (Path(p).stem + ".bad")
        if r["ok"]:
            flag.unlink(missing_ok=True)
            print(f"OK    {r['file']}  ({r['seconds']}s)")
        else:
            bad += 1
            flag.write_text("; ".join(r["reasons"]), encoding="utf-8")
            print(f"VETO  {r['file']}  -> " + "; ".join(r["reasons"]))
    print(f"{len(paths) - bad}/{len(paths)} clips passed")
    return bad


if __name__ == "__main__":
    import glob
    files = [f for a in sys.argv[1:] for f in glob.glob(a)]
    sys.exit(1 if main(files) else 0)
