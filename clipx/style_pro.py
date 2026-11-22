"""PRO Shorts style: face-tracked full-bleed 9:16, slow push-in + beat punch-zooms, bloom glow,
cinematic grade, flash on beats, pop-in word captions, neon title, progress bar.
Usage: python -m clipx.style_pro <manifest.json> --only short05 [--t 12]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from .config import OUT, WORK, HYPE_WORDS
from .edit import PROFANE, _mask, _ts, mute_expr

W, H = 1080, 1920
ACCENT = "&H3CFFB6&"      # lime  (BGR)
NEON_A = "&HFFE500&"      # cyan
NEON_B = "&HE53DFF&"      # pink
MUSIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "music"


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def track_faces(video, dur, iw, ih, step=0.5):
    """Subject x-position (0..1) sampled every `step` s. Face if found, else hold previous."""
    import cv2
    cap = cv2.VideoCapture(str(video))
    cas = [cv2.CascadeClassifier(cv2.data.haarcascades + n) for n in
           ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    xs = []
    for t in np.arange(0, dur, step):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        cx = None
        if ok:
            g = clahe.apply(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
            best = None
            for c in cas:
                for (x, y, w, h) in c.detectMultiScale(g, 1.1, 4, minSize=(max(16, ih // 14),) * 2):
                    if best is None or w * h > best[2] * best[3]:
                        best = (x, y, w, h)
            if best:
                cx = (best[0] + best[2] / 2) / g.shape[1]
        if cx is None and ok:
            # no face: aim at where the detail is (edge energy centroid), not at a stale position
            sm = cv2.resize(g, (160, 90))
            e = np.abs(cv2.Sobel(sm, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(sm, cv2.CV_32F, 0, 1))
            col = e.sum(axis=0) ** 2
            if col.sum() > 0:
                cx = float((col * np.arange(160)).sum() / col.sum() / 160)
        xs.append(cx)
    cap.release()
    known = [x for x in xs if x is not None]
    cur = np.mean(known) if known else 0.5
    out, last = [], cur
    for x in xs:
        if x is not None:
            last = x
        out.append(last)
    # smooth + hysteresis so the camera feels steady, not jittery
    sm, c = [], out[0]
    for x in out:
        if abs(x - c) > 0.04:
            c += (x - c) * 0.35
        sm.append(c)
    return sm, step


def balanced_sum(terms):
    """ffmpeg expressions have a recursion limit; nest sums as a balanced tree."""
    if not terms:
        return "0"
    if len(terms) == 1:
        return terms[0]
    mid = len(terms) // 2
    return f"({balanced_sum(terms[:mid])}+{balanced_sum(terms[mid:])})"


def pulse_expr(times, var, rate):
    return balanced_sum([f"gte({var},{t:.2f})*exp(-({var}-{t:.2f})*{rate})" for t in times])


def pick_beats(words, energy, dur, gap=2.8):
    """Emphasis moments: hype words / exclamations / loudness peaks."""
    cand = []
    for w in words:
        tok = re.sub(r"\W", "", w["w"].lower())
        sc = 0.0
        if tok in HYPE_WORDS:
            sc += 1.0
        if w["w"].endswith(("!", "?")):
            sc += 0.6
        sec = min(int(w["s"]), len(energy) - 1)
        if len(energy):
            sc += max(0, (energy[sec] - energy.mean()) / (energy.std() + 1e-6)) * 0.4
        if sc > 0.5:
            cand.append((sc, w["s"]))
    cand.sort(reverse=True)
    beats = []
    for sc, t in cand:
        if 0.8 < t < dur - 1 and all(abs(t - b) >= gap for b in beats):
            beats.append(t)
        if len(beats) >= dur // 3:
            break
    return sorted(beats)


def build_ass(words, dur, hook, path):
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,Segoe UI Black,88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,7,0,2,50,50,470,1
Style: Hook,Segoe UI Black,104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,1,0,0,100,100,2,0,1,0,0,8,40,40,250,1
Style: Bar,Segoe UI,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    L = []
    # progress bar: clip grows from 0 -> full width over the whole clip
    L.append(f"Dialogue: 5,{_ts(0)},{_ts(dur)},Bar,,0,0,0,,{{\\pos(0,{H - 16})\\p1\\bord0\\shad0\\1c{ACCENT}\\clip(0,0,0,{H})"
             f"\\t(0,{int(dur * 1000)},\\clip(0,0,{W},{H}))}}m 0 0 l {W} 0 {W} 16 0 16")
    if hook:
        parts = hook.upper().split(" ", 1)
        a, b = parts[0], (parts[1] if len(parts) > 1 else "")
        for glow in (True, False):
            if glow:
                sty = "\\bord14\\blur16\\alpha&H70&"
                cA, cB, layer = f"\\1c{NEON_A}\\3c{NEON_A}", f"\\1c{NEON_B}\\3c{NEON_B}", 1
            else:
                sty = "\\bord0\\blur0"
                cA, cB, layer = f"\\1c{NEON_A}", f"\\1c{NEON_B}", 2
            txt = f"{{{sty}\\fad(200,300)\\fscx60\\fscy60\\t(0,260,\\fscx100\\fscy100)}}{{{cA}}}{a}" + (f" {{{cB}}}{b}" if b else "")
            L.append(f"Dialogue: {layer},{_ts(0.15)},{_ts(3.8)},Hook,,0,0,0,,{txt}")
    per = 3
    for i in range(0, len(words), per):
        ch = words[i:i + per]
        chunk_end = ch[-1]["e"] + 0.12
        if i + per < len(words) and words[i + per]["s"] - chunk_end < 0.5:
            chunk_end = words[i + per]["s"]
        # one event per spoken word: that word is lime + pops, the rest white (robust in every renderer)
        for j, w in enumerate(ch):
            st = w["s"] if j else ch[0]["s"]
            en = ch[j + 1]["s"] if j + 1 < len(ch) else chunk_end
            if en <= st:
                continue
            segs = []
            for k, x in enumerate(ch):
                txt = _mask(x["w"]).upper()
                if k == j:
                    segs.append(f"{{\\1c{ACCENT}\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}}{txt}{{\\1c&HFFFFFF&}}")
                else:
                    segs.append(txt)
            L.append(f"Dialogue: 3,{_ts(st)},{_ts(en)},Cap,,0,0,0,,{' '.join(segs)}")
    path.write_text(hdr + "\n".join(L) + "\n", encoding="utf-8")


def render(entry, vid, limit=None):
    from . import ingest
    src = OUT / entry["file"]
    dst = OUT / entry["file"].replace("_raw", "_pro")
    tr = json.loads((WORK / f"{vid}.transcript.json").read_text(encoding="utf-8"))
    st, en = entry["start"], entry["end"]
    dur = en - st if not limit else min(limit, en - st)
    words = [{"w": w["w"], "s": w["s"] - st, "e": w["e"] - st}
             for s in tr for w in s["words"] if st <= w["s"] < st + dur]
    iw, ih = probe(src)
    from . import bars
    bw, bh, bx, by = bars.detect(src, iw, ih)      # real picture area (black bars removed)
    # full-bleed for HD sources; for low-res sources use a shorter frame over a blurred backdrop
    if bh < 720:
        fill = 0.60                      # low-res source
    elif bw / bh > 1.9:
        fill = 0.70                      # cinematic widescreen: a full-height 9:16 slice would cut people off
    else:
        fill = 1.0
    fg_h = int(H * fill) // 2 * 2
    cw = min(bw, int(bh * W / fg_h) // 2 * 2)
    xs, step = track_faces(src, dur, iw, ih)
    knots = []
    for k, cx in enumerate(xs):
        x0 = int(np.clip(cx * iw - cw / 2, bx, bx + bw - cw))
        knots.append((k * step, x0))
    terms = []
    for (t0, x0), (t1, x1) in zip(knots, knots[1:] + [(knots[-1][0] + step, knots[-1][1])]):
        terms.append(f"gte(t,{t0:.2f})*lt(t,{t1:.2f})*({x0}+({x1}-{x0})*(t-{t0:.2f})/{step})")
    xexpr = balanced_sum(terms)

    energy = ingest.audio_energy(src)[: int(dur) + 1]
    beats = pick_beats(words, energy, dur)
    zoom = f"min(1.0+0.08*on/30/{dur:.2f}+0.07*({pulse_expr(beats, 'on/30', 8)}),1.30)"
    flash = f"0.22*({pulse_expr(beats, 't', 14)})"
    hook = entry.get("hook")
    ass = OUT / (dst.stem + ".ass")
    build_ass(words, dur, hook, ass)

    big_w, big_h = 1620, int(1620 * fg_h / W) // 2 * 2
    grade = ("hqdn3d=2.5:2:4:4,normalize=blackpt=black:whitept=white:smoothing=45:independence=0:strength=0.8,"
             "unsharp=5:5:1.0:5:5:0.0,eq=contrast=1.12:saturation=1.25:gamma=1.22")
    g = []
    g.append(f"[0:v]fps=30,crop={cw}:{bh}:x='{xexpr}':y={by},scale={big_w}:{big_h}:flags=lanczos,"
             f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{fg_h}:fps=30,{grade}[fg0]")
    # bloom: blurred copy screened over the sharp frame
    g.append("[fg0]split[s1][s2];[s2]gblur=sigma=22,eq=brightness=-0.05,format=gbrp[bl];"
             "[s1]format=gbrp[s1r];"
             "[s1r][bl]blend=all_mode=screen:all_opacity=0.32,format=yuv420p,vignette=PI/6,"
             f"eq=brightness='{flash}':eval=frame[fg]")
    if fill < 1.0:
        g.append(f"[0:v]crop={bw}:{bh}:{bx}:{by},fps=30,scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
                 "boxblur=45:6,eq=brightness=0.03:saturation=1.5:gamma=1.2[bg];"
                 f"[bg][fg]overlay=0:(H-h)/2,fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.4:.2f}:d=0.4,"
                 f"subtitles={ass.name}[v]")
    else:
        g.append(f"[fg]fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.4:.2f}:d=0.4,subtitles={ass.name}[v]")
    script = OUT / (dst.stem + ".filter.txt")
    script.write_text(";\n".join(g), encoding="utf-8")

    af = "loudnorm=I=-14:TP=-1.5:LRA=11"
    me = mute_expr(words)
    if me:
        af = f"volume=0:enable='{me}'," + af
    af += f",afade=t=in:st=0:d=0.2,afade=t=out:st={dur - 0.4:.2f}:d=0.4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src.name]
    music = sorted(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music[hash(src.name) % len(music)])]
        af_graph = f"[0:a]{af}[v0];[1:a]volume=0.14,afade=t=in:d=1[m];[v0][m]amix=inputs=2:duration=first:normalize=0[a]"
        g_all = script.read_text(encoding="utf-8") + ";\n" + af_graph
        script.write_text(g_all, encoding="utf-8")
        cmd += ["-/filter_complex", script.name, "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-/filter_complex", script.name, "-map", "[v]", "-af", af, "-map", "0:a"]
    cmd += ["-t", str(dur), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst.name]
    subprocess.run(cmd, check=True, cwd=OUT)
    return dst, beats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--only", default="")
    ap.add_argument("--t", type=float, default=None, help="render only first N seconds (preview)")
    a = ap.parse_args()
    mp = Path(a.manifest)
    vid = mp.stem.replace(".manifest", "")
    for e in json.loads(mp.read_text(encoding="utf-8-sig")):
        if e["kind"] == "short" and a.only in e["file"]:
            d, beats = render(e, vid, a.t)
            print("done", d.name, "beats:", [round(b, 1) for b in beats])


if __name__ == "__main__":
    main()
