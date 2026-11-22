"""Original, footage-free Shorts: AI voice + synthwave graphics + animated captions.
Nothing here can be matched by Content ID (no game footage, no copyrighted music).
Usage: python -m clipx.explainer scripts/<name>.json
"""
import asyncio
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import OUT, WORK
from .style_pro import build_ass, W, H

FONT = r"C:\Windows\Fonts\seguibl.ttf"
PALETTES = [  # (sky top, sky horizon, sun top, sun bottom, grid, accent A, accent B)
    ((20, 0, 50), (255, 45, 149), (255, 230, 90), (255, 60, 160), (255, 60, 220), (0, 229, 255), (255, 61, 229)),
    ((5, 10, 50), (0, 180, 255), (170, 255, 240), (80, 120, 255), (0, 220, 255), (182, 255, 60), (0, 229, 255)),
    ((30, 0, 40), (255, 120, 40), (255, 245, 150), (255, 80, 90), (255, 140, 60), (255, 230, 90), (255, 61, 229)),
]


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make_bg(idx, big, sub, out):
    top, hor, st, sb, grid, ca, cb = PALETTES[idx % len(PALETTES)]
    horizon = 1040
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(horizon):
        d.line([(0, y), (W, y)], fill=_lerp(top, hor, (y / horizon) ** 1.6))
    d.rectangle([0, horizon, W, H], fill=(12, 0, 28))
    rnd = random.Random(idx * 7 + 3)
    for _ in range(90):  # stars
        x, y = rnd.randrange(W), rnd.randrange(int(horizon * 0.6))
        r = rnd.choice((1, 1, 2))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
    # striped sun
    R = 330
    sun = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sun)
    for y in range(2 * R):
        sd.line([(0, y), (2 * R, y)], fill=_lerp(st, sb, y / (2 * R)) + (255,))
    mask = Image.new("L", (2 * R, 2 * R), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 2 * R, 2 * R], fill=255)
    md = ImageDraw.Draw(mask)
    for k in range(8):  # stripes cut out of the lower half
        y0 = R + 40 + k * 38
        md.rectangle([0, y0, 2 * R, y0 + 4 + k * 3], fill=0)
    sun.putalpha(mask)
    im.paste(sun, (W // 2 - R, horizon - R - 40), sun)
    # perspective grid floor
    d = ImageDraw.Draw(im)
    for i in range(-14, 15):
        d.line([(W // 2, horizon), (W // 2 + i * 260, H)], fill=grid, width=3)
    for k in range(1, 16):
        y = horizon + int((k / 15) ** 2.2 * (H - horizon))
        d.line([(0, y), (W, y)], fill=grid, width=3)
    # glow
    glow = im.filter(ImageFilter.GaussianBlur(18))
    im = Image.blend(im, Image.composite(glow, im, Image.new("L", im.size, 255)), 0.5)
    # big neon text
    base = ImageDraw.Draw(im)
    words = big.split(" ")
    lines = [" ".join(words)] if len(words) < 3 else [" ".join(words[:2]), " ".join(words[2:])]
    size = 190
    while size > 70:
        f = ImageFont.truetype(FONT, size)
        if max(base.textlength(t, font=f) for t in lines) < W - 120:
            break
        size -= 8
    f = ImageFont.truetype(FONT, size)
    y = 560 - (len(lines) * (size + 10)) // 2
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    pos = []
    for n, t in enumerate(lines):
        x = (W - base.textlength(t, font=f)) / 2
        col = ca if n % 2 == 0 else cb
        ld.text((x, y), t, font=f, fill=col + (255,), stroke_width=10, stroke_fill=col + (255,))
        pos.append((x, y, t, col))
        y += size + 10
    im = Image.alpha_composite(im.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(16)))
    dd = ImageDraw.Draw(im)
    for x, yy, t, col in pos:
        dd.text((x, yy), t, font=f, fill=col, stroke_width=7, stroke_fill=(0, 0, 0))
    if sub:
        sf = ImageFont.truetype(FONT, 58)
        dd.text(((W - dd.textlength(sub, font=sf)) / 2, y + 14), sub, font=sf, fill=(255, 255, 255),
                stroke_width=5, stroke_fill=(0, 0, 0))
    im.convert("RGB").save(out)


async def _tts(text, voice, mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate="+0%", boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"w": ch["text"], "s": ch["offset"] / 1e7, "e": (ch["offset"] + ch["duration"]) / 1e7})
    return words


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def build(script_path):
    sc = json.loads(Path(script_path).read_text(encoding="utf-8-sig"))
    work = WORK / ("exp_" + sc["slug"])
    work.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    clips, all_words, t0 = [], [], 0.0
    for i, s in enumerate(sc["scenes"]):
        mp3 = work / f"s{i}.mp3"
        for attempt in range(4):
            try:
                words = asyncio.run(_tts(s["text"], sc.get("voice", "en-US-AndrewNeural"), mp3))
                break
            except Exception as e:  # voice service sometimes returns no audio; retry
                print(f"  scene {i}: voice retry {attempt + 1} ({type(e).__name__})")
                if attempt == 3:
                    raise
                import time
                time.sleep(2 + attempt * 2)
        d = _dur(mp3) + 0.45
        png = work / f"s{i}.png"
        make_bg(i, s["big"], s.get("sub", ""), png)
        clip = work / f"s{i}.mp4"
        frames = int(d * 30) + 1
        vf = (f"scale=2160:3840,zoompan=z='1.0+0.0007*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:"
              f"s={W}x{H}:fps=30,fade=t=in:st=0:d=0.18:color=white,format=yuv420p")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(png), "-i", str(mp3), "-t", f"{d:.3f}",
                        "-vf", vf, "-af", "apad", "-shortest", "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                        "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", str(clip)], check=True)
        clips.append(clip)
        all_words += [{"w": w["w"], "s": w["s"] + t0, "e": w["e"] + t0} for w in words]
        t0 += d
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    joined = work / "joined.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)],
                   check=True)
    dur = _dur(joined)
    ass = OUT / f"explainer_{sc['slug']}.ass"
    build_ass(all_words, dur, sc.get("hook"), ass)
    final = OUT / f"explainer_{sc['slug']}.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(joined), "-vf", f"subtitles={ass.name}", "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final.name],
                   check=True, cwd=OUT)
    print(f"done {final.name}  {dur:.1f}s")
    return final, sc


if __name__ == "__main__":
    build(sys.argv[1])
