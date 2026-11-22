"""PRO story editor: a JSON spec -> a finished Short (1080x1920) or video (1920x1080).

spec = {
  "slug": "beachfight", "kind": "short" | "video", "src": "work/xxx.mp4", "tag": "GTA 6",
  "title": ["ONE WHAT'S UP", "ONE FIGHT"],          # persistent two-line title (short) / lower-third (video)
  "layout": "tall" | "frame" | "full",               # short only. tall = 4:5 picture over blurred backdrop (default), frame = square, full = 9:16 crop
  "pieces": [ {"s": 612.0, "e": 615.0, "speed": 0.5, "cx": 0.5, "zoom": "in"|"out"|"none", "tr": "cut"|"fade"|"whip"} ... ],
  "caps":   [ {"p": 1, "t": 0.4, "d": 1.3, "text": "I SAID WHAT'S UP"} ... ],   # p = piece index, t = seconds into that piece
  "flash":  [ {"p": 1, "t": 0.0} ],                  # single deliberate white flash
  "sfx":    [ {"p": 0, "t": 0.1, "k": "impact"} ]
}
Calm by design: one deliberate effect per story beat, no constant shake / colour-split / strobing.
CLI: python -m clipx.pro spec.json
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from .config import ROOT, OUT, AUX
from .style_pro import probe, pulse_expr
from . import sfx, framing, tracking
import datetime
from .edit import _ts
from .max import build_ass
import os
# CLIPX_ENCODER=qsv -> Intel Quick Sync (graphics-chip) encoding; default = software x264
_VCODEC = (["-c:v", "h264_qsv", "-preset", "medium", "-global_quality", "21", "-look_ahead", "0"]
           if os.environ.get("CLIPX_ENCODER") == "qsv" else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])

W, H = 1080, 1920
TD = {"cut": 0.05, "fade": 0.25, "whip": 0.30}
XF = {"cut": "fade", "fade": "fade", "whip": "slideleft"}
ACC = ["&H3CFFB6&", "&H00D7FF&", "&HFFD84A&", "&HC850FF&"]


def _atempo(sp):
    if abs(sp - 1) < 1e-3:
        return ""
    parts, s = [], sp
    while s < 0.5:
        parts.append("atempo=0.5"); s /= 0.5
    while s > 2.0:
        parts.append("atempo=2.0"); s /= 2.0
    parts.append(f"atempo={s:.4f}")
    return "," + ",".join(parts)


def timeline(pcs):
    """Pure logic (unit-tested): piece lengths, start times, xfade offsets and total duration."""
    lens = [(p["e"] - p["s"]) / p.get("speed", 1.0) for p in pcs]
    start, T = [0.0], lens[0]
    offs = [0.0]
    for k in range(1, len(pcs)):
        td = TD[pcs[k].get("tr", "fade")]
        off = T - td
        offs.append(off)
        start.append(off)
        T = off + lens[k]
    return lens, start, offs, T


def render(spec):
    src = Path(spec["src"])
    if not src.is_absolute():
        src = (ROOT / src).resolve()
    short = spec.get("kind", "short") == "short"
    vy = spec.get("vy", 0.0)                       # vertical crop offset 0 = top, 1 = bottom
    layout = spec.get("layout", "tall")
    iw, ih = probe(src)
    pcs = spec["pieces"]
    n = len(pcs)
    lens, start, offs, dur = timeline(pcs)

    sq = layout in ("frame", "tall")          # picture sits over a blurred backdrop
    asp = 0.8 if layout == "tall" else 1.0   # crop width / height
    out_w, out_h = ((1080, int(1080 / asp)) if (short and sq) else ((W, H) if short else (1920, 1080)))
    big_w, big_h = (int(out_w * 1.5), int(out_h * 1.5)) if short else (2560, 1440)
    g, cmd = [], ["ffmpeg", "-y", "-v", "error"]
    def _src(p):
        q = Path(p.get("src", spec["src"]))
        return q if q.is_absolute() else (ROOT / q).resolve()
    notes = []
    for p in pcs:
        cmd += ["-ss", f"{p['s']:.3f}", "-t", f"{p['e'] - p['s']:.3f}", "-i", str(_src(p))]
    for k, p in enumerate(pcs):
        sp = p.get("speed", 1.0)
        N = max(int(lens[k] * 30), 2)
        z = p.get("zoom", "in" if k % 2 == 0 else "out")
        amt = 0.07
        zexpr = {"in": f"1+{amt}*on/{N}", "out": f"{1 + amt}-{amt}*on/{N}", "none": "1"}[z]
        cx = p.get("cx", 0.5)
        keys = None
        if cx == "track":                      # opt-in: pan the crop to follow the player (see tracking.py)
            try:
                keys = tracking.track(_src(p), p["s"], p["e"])
            except Exception:
                keys = None
            cx = round(sum(c for _, c in keys) / len(keys), 3) if keys else 0.5
            notes.append(f"piece {k}: player tracking " + (f"on ({len(keys)} keys)" if keys else "found no clear player; static crop"))
        cx = 0.5 if cx == "auto" else cx
        cam, blur = None, ""
        sw, sh = probe(_src(p))
        if spec.get("facecam", True):
            try:
                cam, _, _ = framing.facecam(_src(p), p["s"], p["e"])
            except Exception:
                cam = None
        if cam is not None and short:
            vc_ = spec.get("vcrop", 0.80)
            cw_px = sh * vc_ * (asp if sq else 9 / 16)
            cx, clear = framing.crop_cx_avoiding(cam, sw, sh, cw_px, preferred=cx)
            notes.append(f"piece {k}: streamer webcam detected at {tuple(round(v) for v in cam)}; crop moved to cx={cx:.2f}"
                         + ("" if clear else " (could not fully clear it)"))
        elif cam is not None:
            x0, y0, x1, y1 = [int(v) for v in cam]
            blur = (f"split=2[pa{k}][pb{k}];[pb{k}]crop={x1 - x0}:{y1 - y0}:{x0}:{y0},boxblur=24:6[pc{k}];"
                    f"[pa{k}][pc{k}]overlay={x0}:{y0}[pm{k}];[pm{k}]")
            notes.append(f"piece {k}: streamer webcam detected at {(x0, y0, x1, y1)}; blurred")
        pan = None
        if keys and not (cam is not None and short):     # a detected webcam keeps the static, webcam-avoiding crop
            cwp = sh * (spec.get("vcrop", 0.80) * asp if sq else 9 / 16) if short else None
            if cwp:
                pan = tracking.left_expr(keys, cwp, sw, sp)
        if short and sq:
            vc = spec.get("vcrop", 0.80)       # keep the top 90%: drops baked-in subtitles / channel watermarks at the bottom
            xe = pan or f"(iw-ih*{vc}*{asp})*{cx}"
            crop = f"crop=ih*{vc}*{asp}:ih*{vc}:x='{xe}':y='(ih-ih*{vc})*{vy}'"
        elif short:
            xe = pan or f"(iw-ih*9/16)*{cx}"
            crop = f"crop=ih*9/16:ih:x='{xe}':y=0"
        else:
            vc = spec.get("vcrop", 1.0)
            crop = "null" if vc >= 0.999 else f"crop=iw*{vc}:ih*{vc}:x='(iw-iw*{vc})*{cx}':y='(ih-ih*{vc})*{vy}'"
        sp_f = f"setpts=PTS/{sp:.4f}," if abs(sp - 1) > 1e-3 else ""
        expo = ""
        if spec.get("auto_exposure", True):
            try:
                eg = framing.exposure_gamma(_src(p), p["s"], p["e"])
            except Exception:
                eg = 1.0
            if eg > 1.0:
                expo = f"eq=gamma={eg:.3f},"
                notes.append(f"piece {k}: dark footage, exposure lifted (gamma {eg})")
        head = f"[{k}:v]{sp_f}fps=30," + blur + expo
        g.append(f"{head}{crop},scale={big_w}:{big_h}:flags=lanczos,"
                 f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={out_w}x{out_h}:fps=30,"
                 f"setsar=1,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{k}]")
    prev = "v0"
    for k in range(1, n):
        tr = pcs[k].get("tr", "fade")
        g.append(f"[{prev}][v{k}]xfade=transition={XF[tr]}:duration={TD[tr]}:offset={offs[k]:.3f}[x{k}]")
        prev = f"x{k}"
    flash_t = [start[f["p"]] + f.get("t", 0.0) for f in spec.get("flash", [])]
    flash = f"0.20*({pulse_expr(flash_t, 't', 9)})" if flash_t else "0"
    grade = ("hqdn3d=1.5:1.5:3:3,eq=contrast=1.12:saturation=1.30:gamma=1.10:brightness=0.02,unsharp=5:5:0.8:3:3:0.0,vignette=PI/7,"
             f"eq=brightness='{flash}':eval=frame")
    g.append(f"[{prev}]{grade}[fg]")

    # captions: each phrase is its own caption (two balanced lines), the spoken word highlighted
    words, extra = [], []
    fs_cap = 84 if short else 66
    for ci, c in enumerate(spec.get("caps", [])):
        t0 = start[c["p"]] + c["t"]
        ws = c["text"].upper().split()
        if not ws:
            continue
        per = c["d"] / len(ws)
        tot = sum(len(w) for w in ws) + len(ws) - 1
        brk = None
        if tot > 13 and len(ws) > 1:                       # balanced two-line split
            best = min(range(1, len(ws)), key=lambda i: abs(sum(len(w) for w in ws[:i]) + i - 1 - (sum(len(w) for w in ws[i:]) + len(ws) - i - 1)))
            brk = best
        longest = max(sum(len(w) for w in (ws[:brk] if brk else ws)) + (brk or len(ws)) - 1,
                      sum(len(w) for w in (ws[brk:] if brk else [])) + (len(ws) - brk - 1 if brk else 0))
        fs = int(min(fs_cap, ((W if short else 1920) - 200) / (max(longest, 5) * 0.68)))
        acc = ACC[ci % len(ACC)]
        for i in range(len(ws)):
            parts = []
            for j, w in enumerate(ws):
                if brk is not None and j == brk:
                    parts.append("\\N")
                if j == i:
                    parts.append("{\\1c" + acc + "\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}" + w + "{\\1c&HFFFFFF&}")
                else:
                    parts.append(w)
            txt = " ".join(parts).replace(" \\N ", "\\N")
            a, b = t0 + i * per, t0 + (i + 1) * per
            pre = "\\fad(90,0)" if i == 0 else ""
            extra.append(f"Dialogue: 3,{_ts(a)},{_ts(b)},Cap,,0,0,0,,{{\\fs{fs}{pre}}}" + txt)
    ctr = (W if short else 1920) // 2
    title = spec.get("title")
    if title:
        if short:
            l1, l2 = title[0].upper(), (title[1].upper() if len(title) > 1 else "")
            extra.append(f"Dialogue: 4,{_ts(0)},{_ts(dur)},Hook,,0,0,0,,{{\\an8\\pos({ctr},60)\\fs76\\bord8\\1c&HFFFFFF&\\3c&H000000&}}{l1}")
            if l2:
                extra.append(f"Dialogue: 4,{_ts(0)},{_ts(dur)},Hook,,0,0,0,,{{\\an8\\pos({ctr},150)\\fs92\\bord8\\1c&H8A3CFF&\\3c&H000000&}}{l2}")
        else:
            extra.append(f"Dialogue: 4,{_ts(0.3)},{_ts(min(dur, 6.0))},Hook,,0,0,0,,{{\\an1\\pos(70,980)\\fs70\\bord6\\1c&H3CFFB6&\\3c&H000000&\\fad(250,400)}}{' '.join(title).upper()}")
    if short and sq:
        extra.append(f"Dialogue: 4,{_ts(0.5)},{_ts(dur)},Hook,,0,0,0,,{{\\an8\\pos(540,1730)\\fs44\\bord5\\1c&HFFFFFF&\\3c&H000000&}}FOLLOW FOR MORE GTA 6")
    # on-screen credit to the footage's creator (like GTA-Auto-Clipper's "via ..." line) - credit is courtesy, not permission
    sources = {}
    for p_ in pcs:
        sp_ = _src(p_)
        sources.setdefault(sp_.stem, []).append([p_["s"], p_["e"]])
    meta_of = {}
    for vid_ in sources:
        mf = ROOT / "work" / f"{vid_}.meta.json"
        if mf.exists():
            try:
                meta_of[vid_] = json.loads(mf.read_text(encoding="utf-8-sig"))
            except ValueError:
                pass
    names = []
    for vid_ in sources:
        nm = (meta_of.get(vid_) or {}).get("channel")
        if nm and nm not in names:
            names.append(nm)
    credit = spec.get("credit", " + ".join(names[:2]) if names else None)
    if credit:
        cr = f"via {credit}"
        if short:
            extra.append(f"Dialogue: 5,{_ts(0.4)},{_ts(min(dur, 5.0))},Hook,,0,0,0,,{{\\an8\\pos(540,1668)\\fs32\\bord4\\1c&HFFFFFF&\\3c&H000000&\\fad(200,300)}}{cr}")
        else:
            extra.append(f"Dialogue: 5,{_ts(0.4)},{_ts(min(dur, 5.0))},Hook,,0,0,0,,{{\\an3\\pos(1880,1040)\\fs30\\bord4\\1c&HFFFFFF&\\3c&H000000&\\fad(200,300)}}{cr}")
    slug = spec["slug"]
    ass = AUX / f"pro_{slug}.ass"
    build_ass([], [], dur, None, spec.get("tag", "GTA 6"), None, ass, (W, H) if short else (1920, 1080), extra)
    tail = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.5:.2f}:d=0.5,subtitles={ass.name}[v]"
    if short and sq:
        top = spec.get("frame_y", (1920 - out_h) // 2)
        g.append("[fg]split[a][b];[b]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:6,"
                 f"eq=brightness=-0.14:saturation=1.35[bg];[bg][a]overlay=0:{top},{tail}")
    else:
        g.append(f"[fg]{tail}")

    # audio
    ev = []
    for e in spec.get("sfx", []):
        ev.append((start[e["p"]] + e.get("t", 0.0), e["k"]))
    for k in range(1, n):
        if pcs[k].get("tr", "fade") == "whip":
            ev.append((offs[k], "whoosh"))
    sfx_path = AUX / f"pro_{slug}.sfx.wav"
    sfx.mix(ev, dur, sfx_path)
    cmd += ["-i", sfx_path.name]
    for k, p in enumerate(pcs):
        g.append(f"[{k}:a]aresample=44100{_atempo(p.get('speed', 1.0))},asetpts=PTS-STARTPTS[a{k}]")
    pa = "a0"
    for k in range(1, n):
        g.append(f"[{pa}][a{k}]acrossfade=d={TD[pcs[k].get('tr', 'fade')]}:c1=tri:c2=tri[ax{k}]")
        pa = f"ax{k}"
    fin = f"afade=t=in:st=0:d=0.2,afade=t=out:st={dur - 0.5:.2f}:d=0.5"
    g.append(f"[{pa}]loudnorm=I=-15:TP=-1.5:LRA=11[va];[va][{n}:a]amix=inputs=2:normalize=0:duration=first,"
             f"alimiter=limit=0.95,{fin}[a]")
    script = AUX / f"pro_{slug}.filter.txt"
    script.write_text(";\n".join(g), encoding="utf-8")
    dst = OUT / f"pro_{slug}.mp4"
    cmd += ["-/filter_complex", script.name, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", *_VCODEC, "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True, cwd=AUX)
    meta_dir = AUX / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / f"pro_{slug}.json").write_text(json.dumps({
        "file": dst.name, "kind": spec.get("kind"), "seconds": round(dur, 2),
        "rendered_at": datetime.datetime.now().isoformat(timespec="seconds"), "credit": credit,
        "sources": [{"id": v, "url": (meta_of.get(v) or {}).get("url") or f"https://www.youtube.com/watch?v={v}",
                     "channel": (meta_of.get(v) or {}).get("channel"), "title": (meta_of.get(v) or {}).get("title"),
                     "license": (meta_of.get(v) or {}).get("license"), "ranges": r} for v, r in sources.items()],
        "framing_notes": notes, "spec": spec}, indent=1, ensure_ascii=False), encoding="utf-8")
    return dst, dur


if __name__ == "__main__":
    sp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    d, dur = render(sp)
    print(f"done {d.name} {dur:.1f}s")
