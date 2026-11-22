"""1280x720 thumbnails: best frame (sharp, bright, has a face) + neon title text."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

FONT = r"C:\Windows\Fonts\seguibl.ttf"
CYAN, PINK = (0, 229, 255), (255, 61, 229)


def best_frame(video, n=16):
    from . import bars
    cap = cv2.VideoCapture(str(video))
    fw, fh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    bw, bh, bx, by = bars.detect(video, fw, fh)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    best, bs = None, -1
    for i in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (0.08 + 0.84 * i / n)))
        ok, f = cap.read()
        if not ok:
            continue
        f = f[by:by + bh, bx:bx + bw]
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        bright = g.mean()
        faces = len(cas.detectMultiScale(g, 1.1, 4, minSize=(20, 20)))
        s = sharp * min(bright, 90) / 90 + 150 * min(faces, 2)
        if s > bs:
            best, bs = f, s
    cap.release()
    return Image.fromarray(cv2.cvtColor(best, cv2.COLOR_BGR2RGB))


def _fit_text(draw, text, max_w, size):
    while size > 40:
        f = ImageFont.truetype(FONT, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 6
    return ImageFont.truetype(FONT, 40)


def frame_at(video, t, crop=None):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, fr = cap.read()
    cap.release()
    im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    if crop:                                   # fractional (x0, y0, x1, y1): cut away watermarks / baked-in subtitles
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    return im


def make(video, hook, out, at=None, crop=None):
    im = (frame_at(video, at, crop) if at is not None else best_frame(video)).convert("RGB")
    im = im.resize((1280, int(1280 * im.height / im.width)), Image.LANCZOS)
    if im.height < 720:
        im = im.resize((int(im.width * 720 / im.height), 720), Image.LANCZOS)
    l, t = (im.width - 1280) // 2, (im.height - 720) // 2
    im = im.crop((l, t, l + 1280, t + 720))
    im = ImageEnhance.Brightness(im).enhance(1.35)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    im = ImageEnhance.Color(im).enhance(1.35).filter(ImageFilter.UnsharpMask(2, 120, 3))
    # bottom gradient for text legibility
    grad = Image.new("L", (1, 720))
    for y in range(720):
        grad.putpixel((0, y), int(max(0, (y - 380) / 340) * 200))
    im.paste(Image.new("RGB", (1280, 720), (0, 0, 0)), (0, 0), grad.resize((1280, 720)))
    words = hook.upper().split(" ")
    mid = max(1, len(words) // 2)
    lines = [(" ".join(words[:mid]), CYAN)] + ([(" ".join(words[mid:]), PINK)] if words[mid:] else [])
    d = ImageDraw.Draw(im)
    font = _fit_text(d, max(lines, key=lambda x: len(x[0]))[0], 1120, 150)
    y = 720 - 60 - len(lines) * (font.size + 8)
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for txt, col in lines:
        x = (1280 - d.textlength(txt, font=font)) / 2
        gd.text((x, y), txt, font=font, fill=col + (255,), stroke_width=10, stroke_fill=col + (255,))
        y += font.size + 8
    im = Image.alpha_composite(im.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(14))).convert("RGB")
    d = ImageDraw.Draw(im)
    y = 720 - 60 - len(lines) * (font.size + 8)
    for txt, col in lines:
        x = (1280 - d.textlength(txt, font=font)) / 2
        d.text((x, y), txt, font=font, fill=col, stroke_width=7, stroke_fill=(0, 0, 0))
        y += font.size + 8
    im.save(out, quality=92)
    return out
