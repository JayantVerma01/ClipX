"""MONTAGE mode: multi-shot edit with REAL transitions (xfade: 20 kinds), beat-synced to music, per-shot push-ins /
shakes / speed variants, flash + colour-split on every transition, synth SFX.
Usage: python -m clipx.montage <video file> --kind short|video --dur 45 --tag "GTA 6" --hook "TOP MOMENTS" [--labels "A|B|C"]
Put royalty-free .mp3 files in assets/music for beat-synced cuts (strongly recommended).
"""
import argparse
import re
import subprocess
from pathlib import Path

import numpy as np

from . import bars, sfx
from .config import OUT, AUX
from .max import build_ass, music_beats, ACCENTS
from .style_pro import W, H, MUSIC_DIR, probe, pulse_expr

TRANS = ["fade", "wipeleft", "slideright", "circleopen", "rectcrop", "smoothleft", "zoomin", "pixelize", "radial",
         "diagtl", "hlslice", "vertopen", "squeezeh", "fadewhite", "distance", "dissolve", "hblur", "slideup",
         "wipedown", "circleclose"]
TD = 0.30   # transition length (s)
CALM = True      # default: slow dissolves only, no shake / colour-split / flash. --wild restores the old look
STARTS = None    # optional hand-picked source start times (s), one per shot


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def _ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def scenes_of(src, total):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-vf", "fps=6,scale=320:-2,select='gt(scene,0.30)',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    cuts = [0.0] + sorted({float(x) for x in re.findall(r"pts_time:([\d.]+)", p.stderr)}) + [total]
    return [(a, b) for a, b in zip(cuts, cuts[1:]) if b - a > 0.8]


def subject_x(cap, t, iw):
    import cv2
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    if not ok:
        return 0.5
    g = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
    best = None
    for n in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
        for (x, y, w, h) in cv2.CascadeClassifier(cv2.data.haarcascades + n).detectMultiScale(g, 1.1, 4, minSize=(24, 24)):
            if best is None or w * h > best[2] * best[3]:
                best = (x, y, w, h)
    if best:
        return (best[0] + best[2] / 2) / g.shape[1]
    sm = cv2.resize(g, (160, 90))
    e = np.abs(cv2.Sobel(sm, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(sm, cv2.CV_32F, 0, 1))
    col = e.sum(axis=0) ** 2
    return float((col * np.arange(160)).sum() / col.sum() / 160) if col.sum() > 0 else 0.5


def plan(src, kind, total, mfile):
    """Returns (boundaries, lens, shots): boundaries[k] = timeline start of shot k; shots = [(src_start, src_len, speed)]."""
    sdur = _dur(src)
    min_len = 1.6 if kind == "short" else 3.5
    if mfile:
        beats = [x for x in music_beats(mfile, total) if x < total]
        b, last = [0.0], 0.0
        for t in beats:                       # cut on beats, but never shorter than min_len
            if t - last >= min_len:
                b.append(t)
                last = t
    else:
        step = 2.4 if kind == "short" else 5.0
        b = [i * step for i in range(int(total / step))]
    b = [x for x in b if x < total - 1.0] or [0.0]
    b.append(total)                            # end marker
    lens = [b[k + 1] - b[k] for k in range(len(b) - 1)]
    if STARTS:
        n = len(STARTS)
        lens = [total / n] * n
        b = [k * total / n for k in range(n)]
        shots = [(float(t), round((lens[k] + TD) * 1.0, 2), 1.0) for k, t in enumerate(STARTS)]
        return b, lens, shots
    scenes = scenes_of(src, sdur)
    avg = max(sum(lens) / len(lens), 1.5)
    pool = []
    for s, e in scenes:
        t = s + 0.15
        while t + avg + TD < e:
            pool.append(t)
            t += avg + 0.4
    if len(pool) < len(lens):                   # not enough scene-based windows: even spread
        pool = list(np.linspace(0, max(sdur - avg - 1, 0), max(len(lens), 2)))
    idx = np.linspace(0, len(pool) - 1, len(lens)).astype(int)
    shots = []
    for k, i in enumerate(idx):
        speed = [1.0, 1.0, 1.25, 1.0, 0.8][k % 5] if mfile else 1.0
        need = (lens[k] + TD) * speed
        start = min(pool[i], max(sdur - need - 0.2, 0))
        shots.append((round(start, 2), round(need, 2), speed))
    return b[:-1], lens, shots


def render(src, kind="short", total=45.0, tag="GTA 6", hook="TOP MOMENTS", labels=None, slug="montage", badge=None):
    import cv2
    global TD
    TD = 0.7 if CALM else 0.30
    src = Path(src).resolve()
    music = sorted(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    mfile = music[hash(src.name) % len(music)] if music else None
    short = kind == "short"
    canvas = (W, H) if short else (1920, 1080)
    iw, ih = probe(src)
    bw, bh, bx, by = bars.detect(src, iw, ih)
    if not short or (bh >= 720 and bw / bh <= 1.9):
        fill = 1.0
    else:
        fill = 0.70 if bh >= 720 else 0.60
    fg_h = int(H * fill) // 2 * 2 if short else 1080
    fg_w = W if short else 1920
    cw = min(bw, int(bh * fg_w / fg_h) // 2 * 2)

    b, lens, shots = plan(src, kind, total, mfile)
    n = len(shots)
    cap = cv2.VideoCapture(str(src))
    grade = ("hqdn3d=2:1.5:3:3,normalize=blackpt=black:whitept=white:smoothing=30:independence=0:strength=0.7,"
             "unsharp=5:5:1.0:5:5:0.0,eq=contrast=1.14:saturation=1.30:gamma=1.12")
    g = []
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for (s0, need, sp) in shots:
        cmd += ["-ss", f"{s0:.2f}", "-t", f"{need:.2f}", "-i", str(src)]
    for k, (s0, need, sp) in enumerate(shots):
        d = lens[k] + TD
        frames = int(d * 30) + 1
        amt = 0.06 if CALM else 0.14
        zin = f"1.0+{amt}*on/{frames}" if k % 2 == 0 else f"1.{int(amt*100):02d}-{amt}*on/{frames}"
        shx = shy = ""
        if k % 3 == 1 and not CALM:                   # impact shake at the start of some shots
            shx = "+26*sin(85*on/30)*exp(-on/30*6)"
            shy = "+20*cos(70*on/30)*exp(-on/30*6)"
        if short:
            cx = (subject_x(cap, s0 + need * 0.3, iw) + subject_x(cap, s0 + need * 0.7, iw)) / 2
            x0 = int(np.clip(cx * iw - cw / 2, bx, bx + bw - cw))
            geo = (f"crop={cw}:{bh}:{x0}:{by},scale=1620:{int(1620 * fg_h / W) // 2 * 2}:flags=lanczos,"
                   f"zoompan=z='{zin}':x='iw/2-(iw/zoom/2){shx}':y='ih/2-(ih/zoom/2){shy}':d=1:s={W}x{fg_h}:fps=30")
        else:
            geo = (f"crop={bw}:{bh}:{bx}:{by},scale=2880:1620:force_original_aspect_ratio=decrease:flags=lanczos,"
                   f"pad=2880:1620:(ow-iw)/2:(oh-ih)/2,"
                   f"zoompan=z='{zin}':x='iw/2-(iw/zoom/2){shx}':y='ih/2-(ih/zoom/2){shy}':d=1:s=1920x1080:fps=30")
        sp_f = f"setpts=PTS/{sp}," if sp != 1.0 else ""
        g.append(f"[{k}:v]{sp_f}fps=30,{geo},{grade},setsar=1,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{k}]")
    cap.release()

    # xfade chain: each transition starts TD before the previous shot ends
    T = lens[0] + TD
    prev = "v0"
    tr_times = []
    for k in range(1, n):
        off = T - TD
        tr = "fade" if CALM else TRANS[(k * 7 + 3) % len(TRANS)]
        g.append(f"[{prev}][v{k}]xfade=transition={tr}:duration={TD}:offset={off:.3f}[x{k}]")
        tr_times.append(off)
        prev = f"x{k}"
        T = off + lens[k] + TD
    dur = min(T, total + TD)

    fx = []
    for i, t in enumerate([] if CALM else tr_times):
        fx.append(f"rgbashift=rh=-14:bh=14:enable='between(t,{t:.2f},{t + TD + 0.08:.2f})'")
        if i % 3 == 2:
            fx.append(f"noise=alls=40:allf=t:enable='between(t,{t:.2f},{t + 0.2:.2f})'")
    fxs = ("," + ",".join(fx)) if fx else ""
    flash = f"0.28*({pulse_expr([t + TD * 0.5 for t in tr_times] + [0.2], 't', 11)})" if not CALM else "0"
    g.append(f"[{prev}]format=gbrp,split[a1][a2];[a2]gblur=sigma=22,eq=brightness=-0.05[bl];"
             f"[a1][bl]blend=all_mode=screen:all_opacity=0.30,format=yuv420p,vignette=PI/6,"
             f"eq=brightness='{flash}':eval=frame{fxs}{"" if CALM else ",noise=alls=5:allf=t"}[fgx]")

    extra = []
    if labels:
        ctr = canvas[0] // 2
        for k, lb in enumerate(labels[: len(b)]):
            if not lb.strip():
                continue
            t0 = b[k] + (0 if k == 0 else TD)
            t1 = b[k + 1] if k + 1 < len(b) else dur
            extra.append(f"Dialogue: 3,{_ts(t0)},{_ts(t1)},Hook,,0,0,0,,{{\\an8\\pos({ctr},{360 if short else 220})"
                         f"\\1c{ACCENTS[k % 4]}\\bord6\\fscx60\\fscy60\\t(0,120,\\fscx100\\fscy100)\\fad(60,100)}}{lb.upper()}")
    ass = AUX / f"montage_{slug}_{kind}.ass"
    build_ass([], [], dur, hook, tag, badge, ass, canvas, extra)
    tail = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.5:.2f}:d=0.5,subtitles={ass.name}[v]"
    if short and fill < 1.0:
        g.append(f"[fgx]split[f1][f2];[f1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=45:6,"
                 f"eq=brightness=0.03:saturation=1.5:gamma=1.2[bg];[bg][f2]overlay=0:(H-h)/2,{tail}")
    else:
        g.append(f"[fgx]{tail}")

    ev = [(0.1, "impact")] if not CALM else []
    for t in ([] if CALM else tr_times):
        ev += [(t, "whoosh"), (t + TD * 0.9, "impact")]
    sfx_path = AUX / f"montage_{slug}_{kind}.sfx.wav"
    sfx.mix(ev, dur, sfx_path)
    cmd += ["-i", sfx_path.name]
    si = n
    fin = f"afade=t=in:st=0:d=0.3,afade=t=out:st={dur - 0.8:.2f}:d=0.8"
    if mfile:
        cmd += ["-stream_loop", "-1", "-i", str(mfile)]
        g.append(f"[{si + 1}:a]atrim=0:{dur:.2f},asetpts=PTS-STARTPTS,volume=0.9[m];"
                 f"[m][{si}:a]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95,{fin}[a]")
    else:
        prev_a = "0:a"
        for k in range(1, n):
            g.append(f"[{prev_a}][{k}:a]acrossfade=d={TD}[ax{k}]")
            prev_a = f"ax{k}"
        g.append(f"[{prev_a}]loudnorm=I=-15:TP=-1.5:LRA=11[va];[va][{si}:a]amix=inputs=2:normalize=0:duration=first,"
                 f"alimiter=limit=0.95,{fin}[a]")
    script = AUX / f"montage_{slug}_{kind}.filter.txt"
    script.write_text(";\n".join(g), encoding="utf-8")
    dst = OUT / f"montage_{slug}_{kind}.mp4"
    cmd += ["-/filter_complex", script.name, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", "-c:v", "libx264",
            "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True, cwd=AUX)
    return dst, dur, n, mfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--kind", choices=["short", "video"], default="short")
    ap.add_argument("--dur", type=float, default=45.0)
    ap.add_argument("--tag", default="GTA 6")
    ap.add_argument("--hook", default="TOP MOMENTS")
    ap.add_argument("--labels", default=None, help="pipe-separated text per shot, e.g. '#1 CARS|#2 CHASE'")
    ap.add_argument("--badge", default=None)
    ap.add_argument("--slug", default="montage")
    ap.add_argument("--wild", action="store_true")
    ap.add_argument("--starts", default=None, help="comma-separated source start seconds, one per shot")
    a = ap.parse_args()
    global CALM, STARTS
    CALM = not a.wild
    STARTS = [float(x) for x in a.starts.split(",")] if a.starts else None
    d, dur, n, m = render(a.src, a.kind, a.dur, a.tag, a.hook, a.labels.split("|") if a.labels else None, a.slug, a.badge)
    print(f"done {d.name}  {dur:.1f}s  {n} shots  music={'yes' if m else 'no (source audio)'}")


if __name__ == "__main__":
    main()
