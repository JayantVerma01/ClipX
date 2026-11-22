"""MAX style: face-tracked 9:16 + cut-hiding FX (whip blur, glitch, flash, zoom punch, shake, colour split),
synth SFX, music ducking, chips + top subtitles + animated pop captions.
Usage: python -m clipx.max <manifest.json> --only short01 [--t 25] [--tag "GTA 6"] [--badge "#1/5"]
Drop royalty-free .mp3 files into assets/music to get a ducked music bed + beat-synced FX.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from . import bars, sfx
from .config import OUT, RAW, AUX, WORK, HYPE_WORDS
from .edit import PROFANE, _mask, _ts, mute_expr
from .style_pro import (W, H, ACCENT, NEON_A, NEON_B, MUSIC_DIR, probe, track_faces, pulse_expr,
                        balanced_sum, pick_beats)

ACCENTS = ["&H3CFFB6&", "&H00E6FF&", "&HFFE500&", "&HE53DFF&"]   # lime, yellow, cyan, pink (BGR)
CUT_KINDS = ["whip", "glitch", "flash"]
BEAT_KINDS = ["punch", "shake", "chroma"]
SFX_FOR = {"whip": "whoosh", "glitch": "glitch", "flash": "impact", "punch": "impact", "shake": "impact", "chroma": "pop"}


# ---------- analysis ----------
def scene_cuts(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", "scale=320:-2,select='gt(scene,0.30)',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    return sorted({float(x) for x in re.findall(r"pts_time:([\d.]+)", p.stderr)})


def music_beats(path, dur):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", str(dur + 2), "-vn", "-ac", "1", "-ar", "11025",
                        "-f", "s16le", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32)
    hop = 256
    n = len(a) // hop
    if n < 10:
        return []
    e = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    flux = np.maximum(np.diff(e, prepend=e[0]), 0)
    thr = flux.mean() + 1.0 * flux.std()
    beats, last = [], -9
    for i, v in enumerate(flux):
        t = i * hop / 11025
        if v > thr and t - last > 0.4:
            beats.append(t)
            last = t
    return beats


def make_events(cuts, beats, dur, snap=None):
    ev = [(0.2, "flash")]
    for i, t in enumerate(cuts):
        if 0.8 < t < dur - 0.6:
            ev.append((t, CUT_KINDS[i % 3]))
    for i, t in enumerate(beats):
        if 0.8 < t < dur - 0.6:
            ev.append((t, BEAT_KINDS[i % 3]))
    ev.sort()
    out, last = [], -9
    for t, k in ev:
        if t - last >= 0.9:
            out.append((round(t, 2), k))
            last = t
    return out[: max(4, int(dur / 1.8))]


# ---------- subtitles / graphics ----------
def build_ass(words, segs, dur, hook, tag, badge, path, canvas=(W, H), extra=None):
    W, H = canvas                       # shadows the module constants: works for 1080x1920 and 1920x1080
    vd = W > H                          # widescreen video mode
    capS, capM, subS, subM, tagS, hookS, hookM, mL = ((64, 170, 32, 60, 30, 84, 140, 50) if vd
                                                       else (92, 470, 42, 170, 40, 104, 300, 60))
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,Segoe UI Black,{capS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,8,0,2,50,50,{capM},1
Style: Sub,Segoe UI Semibold,{subS},&H00FFFFFF,&H00FFFFFF,&H99000000,&H99000000,0,0,0,0,100,100,0,0,3,14,0,8,90,90,{subM},1
Style: Tag,Segoe UI Black,{tagS},&H00000000,&H00000000,&H3CFFB6,&H3CFFB6,-1,0,0,0,100,100,2,0,3,12,0,7,{mL},0,{mL},1
Style: Badge,Segoe UI Black,{tagS + 4},&H00FFFFFF,&H00FFFFFF,&H3030E0,&H3030E0,-1,0,0,0,100,100,2,0,3,12,0,9,0,{mL},{mL},1
Style: Hook,Segoe UI Black,{hookS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,1,0,0,100,100,2,0,1,0,0,8,40,40,{hookM},1
Style: Bar,Segoe UI,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    L = []
    L.append(f"Dialogue: 5,{_ts(0)},{_ts(dur)},Bar,,0,0,0,,{{\\pos(0,{H - 16})\\p1\\bord0\\shad0\\1c{ACCENT}\\clip(0,0,0,{H})"
             f"\\t(0,{int(dur * 1000)},\\clip(0,0,{W},{H}))}}m 0 0 l {W} 0 {W} 16 0 16")
    if tag:
        L.append(f"Dialogue: 4,{_ts(0)},{_ts(dur)},Tag,,0,0,0,,{{\\fad(250,0)}}{tag.upper()}")
    if badge:
        L.append(f"Dialogue: 4,{_ts(0)},{_ts(dur)},Badge,,0,0,0,,{{\\fad(250,0)}}{badge}")
    if hook:
        a, _, b = hook.upper().partition(" ")
        for glow in (True, False):
            sty, cA, cB, layer = (("\\bord14\\blur16\\alpha&H70&", f"\\1c{NEON_A}\\3c{NEON_A}", f"\\1c{NEON_B}\\3c{NEON_B}", 1)
                                  if glow else ("\\bord0\\blur0", f"\\1c{NEON_A}", f"\\1c{NEON_B}", 2))
            # glitch-in: starts jittering sideways then locks
            anim = "\\fscx140\\fscy60\\t(0,160,\\fscx100\\fscy100)" if not glow else "\\fscx140\\fscy60\\t(0,160,\\fscx100\\fscy100)"
            L.append(f"Dialogue: {layer},{_ts(0.15)},{_ts(3.6)},Hook,,0,0,0,,{{{sty}\\fad(120,300){anim}}}{{{cA}}}{a}"
                     + (f" {{{cB}}}{b}" if b else ""))
    # in-game-style sentence subtitles on top
    for s in segs:
        st, en = max(s["start"], 0.0), min(s["end"], dur)
        if en - st < 0.3:
            continue
        txt = " ".join(_mask(w) for w in s["text"].split())
        L.append(f"Dialogue: 2,{_ts(st)},{_ts(en)},Sub,,0,0,0,,{{\\fad(80,80)}}{txt}")
    # big animated captions: one event per spoken word, 3 animation styles rotating
    per = 3
    for ci, i in enumerate(range(0, len(words), per)):
        ch = words[i:i + per]
        chunk_end = ch[-1]["e"] + 0.12
        if i + per < len(words) and words[i + per]["s"] - chunk_end < 0.5:
            chunk_end = words[i + per]["s"]
        acc = ACCENTS[ci % 4]
        mode = ci % 3
        n_chars = sum(len(x["w"]) for x in ch) + len(ch) - 1
        cs = int(min(capS, (W - 160) / (max(n_chars, 4) * 0.70)))     # shrink long chunks so they never leave the screen
        for j, w in enumerate(ch):
            st = w["s"] if j else ch[0]["s"]
            en = ch[j + 1]["s"] if j + 1 < len(ch) else chunk_end
            if en <= st:
                continue
            segs_t = []
            for k, x in enumerate(ch):
                txt = _mask(x["w"]).upper()
                tok = re.sub(r"\W", "", x["w"].lower())
                if k == j:
                    big = f"\\fs{int(cs * 1.15)}" if (tok in HYPE_WORDS and n_chars <= 12) else ""
                    segs_t.append(f"{{\\1c{acc}{big}\\fscx114\\fscy114\\t(0,90,\\fscx100\\fscy100)}}{txt}{{\\1c&HFFFFFF&\\fs{cs}}}")
                else:
                    segs_t.append(txt)
            first = (j == 0)
            if mode == 0 and first:
                pre = "\\fscx60\\fscy60\\t(0,90,\\fscx100\\fscy100)"
            elif mode == 1 and first:
                pre = f"\\an2\\move({W // 2},{H - capM + 60},{W // 2},{H - capM},0,120)"
            elif mode == 2 and first:
                pre = "\\frz-5\\t(0,110,\\frz0)"
            else:
                pre = ""
            L.append(f"Dialogue: 3,{_ts(st)},{_ts(en)},Cap,,0,0,0,,{{\\fs{cs}{pre}}}" + " ".join(segs_t))
    L += (extra or [])
    path.write_text(hdr + "\n".join(L) + "\n", encoding="utf-8")


# ---------- main render ----------
CALM = True   # default: clean, watchable edit. Run with --wild for the old effect-heavy look.


def render(entry, vid, limit=None, tag="GTA 6", badge=None):
    src = RAW / entry["file"]
    dst = OUT / entry["file"].replace("_raw", "_max")
    tr = json.loads((WORK / f"{vid}.transcript.json").read_text(encoding="utf-8-sig"))
    st, en = entry["start"], entry["end"]
    dur = en - st if not limit else min(limit, en - st)
    words = [{"w": w["w"], "s": w["s"] - st, "e": w["e"] - st}
             for s in tr for w in s["words"] if st <= w["s"] < st + dur]
    segs = [{"text": s["text"], "start": s["start"] - st, "end": s["end"] - st}
            for s in tr if st <= s["start"] < st + dur]

    iw, ih = probe(src)
    bw, bh, bx, by = bars.detect(src, iw, ih)
    video = entry["kind"] == "video"      # widescreen 1920x1080 long-form
    canvas = (1920, 1080) if video else (W, H)
    if bh < 720:
        fill = 0.60
    elif bw / bh > 1.9:
        fill = 0.70
    else:
        fill = 1.0
    fg_h = int(H * fill) // 2 * 2
    cw = min(bw, int(bh * W / fg_h) // 2 * 2)
    xexpr = "0"
    if not video:
        xs, step = track_faces(src, dur, iw, ih)
        terms = []
        knots = [(k * step, int(np.clip(cx * iw - cw / 2, bx, bx + bw - cw))) for k, cx in enumerate(xs)]
        for (t0, x0), (t1, x1) in zip(knots, knots[1:] + [(knots[-1][0] + step, knots[-1][1])]):
            terms.append(f"gte(t,{t0:.2f})*lt(t,{t1:.2f})*({x0}+({x1}-{x0})*(t-{t0:.2f})/{step})")
        xexpr = balanced_sum(terms)

    # events: scene cuts + emphasis beats (snapped to music beats if music exists)
    music = sorted(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    mfile = music[hash(src.name) % len(music)] if music else None
    from . import ingest
    energy = ingest.audio_energy(src)[: int(dur) + 1]
    cuts = [c for c in scene_cuts(src) if c < dur]
    beats = pick_beats(words, energy, dur)
    if mfile:
        mb = music_beats(mfile, dur)
        if mb:
            beats = [min(mb, key=lambda b: abs(b - t)) for t in beats] + [b for b in mb[::2]]
    ev = make_events(cuts, sorted(set(beats)), dur)
    if CALM:
        # calm mode: ONE soft intro flash + a gentle zoom nudge at most every ~6s. No shake / blur / chroma / glitch.
        ev, last = [(0.2, "flash")], 0.2
        for t, k in sorted([(t, "punch") for t in beats]):
            if 1.5 < t < dur - 1.0 and t - last >= 6.0:
                ev.append((round(t, 2), "punch"))
                last = t

    zoom_t = [t for t, k in ev if k in ("punch", "flash", "whip")]
    shake_t = [t for t, k in ev if k in ("shake", "glitch")]
    flash_t = [t for t, k in ev if k == "flash"]
    # full-bleed 9:16 from 16:9 gameplay: start zoomed in (1.17) and anchored high, which also crops away the
    # game's own baked-in subtitles along the bottom edge
    base = 1.17 if (not video and fill == 1.0) else 1.0
    yanchor = "(ih-ih/zoom)*0.10" if base > 1 else "ih/2-(ih/zoom/2)"
    zoom = f"min({base}+0.08*on/30/{dur:.2f}+{0.045 if CALM else 0.10}*({pulse_expr(zoom_t, 'on/30', 4 if CALM else 9)}),{base + 0.34})"
    shx = f"30*sin(85*on/30)*({pulse_expr(shake_t, 'on/30', 6)})"
    shy = f"22*cos(70*on/30)*({pulse_expr(shake_t, 'on/30', 6)})"
    fx = []
    for t, k in ev:
        if k in ("glitch", "chroma", "whip"):
            fx.append(f"rgbashift=rh=-16:bh=16:gv=3:enable='between(t,{t:.2f},{t + 0.22:.2f})'")
        if k == "whip":
            fx.append(f"gblur=sigma=45:sigmaV=0.5:enable='between(t,{t:.2f},{t + 0.16:.2f})'")
        if k == "glitch":
            fx.append(f"noise=alls=50:allf=t:enable='between(t,{t:.2f},{t + 0.2:.2f})'")
    fxs = ("," + ",".join(fx)) if fx else ""
    flash = f"{0.18 if CALM else 0.32}*({pulse_expr(flash_t, 't', 12)})"

    ass = AUX / (dst.stem + ".ass")
    build_ass(words, segs, dur, entry.get("hook"), tag, badge, ass, canvas)

    big_w, big_h = 1620, int(1620 * fg_h / W) // 2 * 2
    grade = ("hqdn3d=2.5:2:4:4,normalize=blackpt=black:whitept=white:smoothing=45:independence=0:strength=0.8,"
             "unsharp=5:5:1.0:5:5:0.0,eq=contrast=1.14:saturation=1.30:gamma=1.15")
    if video:
        shx, shy = shx.replace("30*", "40*"), shy.replace("22*", "28*")
        head = (f"[0:v]fps=30,crop={bw}:{bh}:{bx}:{by},scale=2880:1620:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad=2880:1620:(ow-iw)/2:(oh-ih)/2,"
                f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)+{shx}':y='ih/2-(ih/zoom/2)+{shy}':d=1:s=1920x1080:fps=30,")
    else:
        head = (f"[0:v]fps=30,crop={cw}:{bh}:x='{xexpr}':y={by},scale={big_w}:{big_h}:flags=lanczos,"
                f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)+{shx}':y='{yanchor}+{shy}':d=1:s={W}x{fg_h}:fps=30,")
    g = [head + f"{grade}{fxs}{"" if CALM else ",noise=alls=3:allf=t"}[fg0]",
         "[fg0]split[s1][s2];[s2]gblur=sigma=22,eq=brightness=-0.05,format=gbrp[bl];[s1]format=gbrp[s1r];"
         f"[s1r][bl]blend=all_mode=screen:all_opacity=0.32,format=yuv420p,vignette=PI/6,"
         f"eq=brightness='{flash}':eval=frame[fg]"]
    tail = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.4:.2f}:d=0.4,subtitles={ass.name}[v]"
    if fill < 1.0 and not video:
        g.append(f"[0:v]crop={bw}:{bh}:{bx}:{by},fps=30,scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
                 "crop=1080:1920,boxblur=45:6,eq=brightness=0.03:saturation=1.5:gamma=1.2[bg];"
                 f"[bg][fg]overlay=0:(H-h)/2,{tail}")
    else:
        g.append(f"[fg]{tail}")

    # audio: voice + synth SFX (+ ducked music)
    sfx_path = AUX / (dst.stem + ".sfx.wav")
    sfx.mix([(0.15, "impact")] + [(t, SFX_FOR[k]) for t, k in ev[1:]], dur, sfx_path)
    me = mute_expr(words)
    vo = "[0:a]" + (f"volume=0:enable='{me}'," if me else "") + "loudnorm=I=-15:TP=-1.5:LRA=11"
    fin = f"afade=t=in:st=0:d=0.2,afade=t=out:st={dur - 0.4:.2f}:d=0.4"
    if mfile:
        g.append(f"{vo},asplit=2[va][vb];[2:a]volume=0.30,afade=t=in:d=1,afade=t=out:st={dur - 1.2:.2f}:d=1.2[m];"
                 "[m][vb]sidechaincompress=threshold=0.03:ratio=12:attack=10:release=300[md];"
                 f"[va][md][1:a]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95,{fin}[a]")
    else:
        g.append(f"{vo}[va];[va][1:a]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95,{fin}[a]")
    script = AUX / (dst.stem + ".filter.txt")
    script.write_text(";\n".join(g), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", sfx_path.name]
    if mfile:
        cmd += ["-stream_loop", "-1", "-i", str(mfile)]
    cmd += ["-/filter_complex", script.name, "-map", "[v]", "-map", "[a]", "-t", str(dur), "-c:v", "libx264",
            "-preset", "veryfast" if CALM else "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True, cwd=AUX)
    return dst, ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--only", default="")
    ap.add_argument("--t", type=float, default=None)
    ap.add_argument("--tag", default="GTA 6")
    ap.add_argument("--badge", default=None)
    ap.add_argument("--wild", action="store_true")
    a = ap.parse_args()
    global CALM
    CALM = not a.wild
    mp = Path(a.manifest)
    vid = mp.stem.replace(".manifest", "")
    for e in json.loads(mp.read_text(encoding="utf-8-sig")):
        if a.only in e["file"]:
            d, ev = render(e, vid, a.t, a.tag, a.badge)
            print("done", d.name, "events:", ev)


if __name__ == "__main__":
    main()
