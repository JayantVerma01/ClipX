"""Edit raw clips: upscale + clean, color grade, loudness, fades, animated captions, profanity bleep.
Usage: python -m clipx.edit <manifest.json> [--only NAME_SUBSTRING]
"""
import argparse
import json
import re
import subprocess
from .config import OUT, WORK

PROFANE = re.compile(r"(fuck|shit|bitch|cunt|dick|asshole|bastard|pussy|nigg|whore|slut)", re.I)
HOOK_SEC = 3.0


def _ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def _mask(w):
    core = re.sub(r"[^\w']", "", w)
    if PROFANE.search(core):
        return w[0] + "*" * (len(w) - 1) if len(w) > 1 else w
    return w


def build_ass(words, kind, hook, path):
    short = kind == "short"
    W, H = (1080, 1920) if short else (1920, 1080)
    size = 84 if short else 60
    marginv = 560 if short else 70
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,Arial Black,{size},&H0000E5FF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,7,3,2,60,60,{marginv},1
Style: Hook,Arial Black,{int(size*0.85)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,7,3,8,60,60,{200 if short else 60},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = []
    if hook:
        lines.append(f"Dialogue: 1,{_ts(0.2)},{_ts(HOOK_SEC)},Hook,,0,0,0,,{{\\fad(150,250)}}{hook.upper()}")
    per = 3 if short else 6
    for i in range(0, len(words), per):
        ch = words[i:i + per]
        if not ch:
            continue
        st, en = ch[0]["s"], ch[-1]["e"]
        # pull end to the next chunk start if the gap is small so captions don't flicker
        if i + per < len(words) and words[i + per]["s"] - en < 0.4:
            en = words[i + per]["s"]
        parts = []
        for j, w in enumerate(ch):
            nxt = ch[j + 1]["s"] if j + 1 < len(ch) else en
            cs = max(int(round((nxt - w["s"]) * 100)), 1)
            parts.append(f"{{\\k{cs}}}{_mask(w['w']).upper()}")
        lines.append(f"Dialogue: 0,{_ts(st)},{_ts(en)},Cap,,0,0,0,,{{\\fad(40,40)}}" + " ".join(parts))
    path.write_text(hdr + "\n".join(lines) + "\n", encoding="utf-8")


def mute_expr(words):
    ranges = [f"between(t,{w['s'] - 0.03:.2f},{w['e'] + 0.03:.2f})" for w in words
              if PROFANE.search(re.sub(r"[^\w']", "", w["w"]))]
    return "+".join(ranges)


def edit_clip(entry, vid):
    kind = entry["kind"]
    src = OUT / entry["file"]
    dst = OUT / entry["file"].replace("_raw", "_final")
    tr = json.loads((WORK / f"{vid}.transcript.json").read_text(encoding="utf-8"))
    st, en = entry["start"], entry["end"]
    dur = en - st
    words = [{"w": w["w"], "s": w["s"] - st, "e": w["e"] - st}
             for s in tr for w in s["words"] if st <= w["s"] < en]
    ass = OUT / (dst.stem + ".ass")
    build_ass(words, kind, entry.get("hook"), ass)

    # clean + sharpen + grade (applied after upscale)
    # normalize = auto-levels (lifts dark scenes, smoothed over time so no flicker)
    grade = ("hqdn3d=3:2:4:4,normalize=blackpt=black:whitept=white:smoothing=45:strength=0.7,"
             "unsharp=5:5:0.9:5:5:0.0,"
             "eq=contrast=1.08:saturation=1.20:gamma=1.12")
    fade = f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.45:.2f}:d=0.45"
    if kind == "short":
        vf = (f"[0:v]split[a][b];"
              f"[a]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,boxblur=40:6,eq=brightness=0.04:saturation=1.4:gamma=1.25[bg];"
              f"[b]scale=1080:-2:flags=lanczos,{grade}[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{fade},subtitles={ass.name}[v]")
    else:
        vf = (f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
              f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,{grade},{fade},subtitles={ass.name}[v]")
    af = "loudnorm=I=-14:TP=-1.5:LRA=11"
    me = mute_expr(words)
    if me:
        af = f"volume=0:enable='{me}'," + af
    af += f",afade=t=in:st=0:d=0.25,afade=t=out:st={dur - 0.4:.2f}:d=0.4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src.name, "-filter_complex", vf, "-map", "[v]", "-af", af,
           "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst.name]
    subprocess.run(cmd, check=True, cwd=OUT)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    from pathlib import Path
    mp = Path(a.manifest)
    vid = mp.stem.replace(".manifest", "")
    for e in json.loads(mp.read_text(encoding="utf-8-sig")):
        if a.only in e["file"]:
            print("editing", e["file"])
            print("  ->", edit_clip(e, vid).name)


if __name__ == "__main__":
    main()
