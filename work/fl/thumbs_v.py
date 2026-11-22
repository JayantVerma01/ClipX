import sys
sys.path.insert(0, ".")
from pathlib import Path
from PIL import Image
from clipx import thumb
T = Path("other/thumbs")
T.mkdir(parents=True, exist_ok=True)
C = (0.03, 0.03, 0.97, 0.86)          # trims corner watermarks + baked-in subtitles
jobs = [
    ("v_beachrampage", "8-DRGbQ1IXc", 226.0, "5-STAR RAMPAGE"),
    ("v_policechase", "9TLwyuGDSmI", 198.0, "POLICE CHASE"),
    ("v_tankvspolice", "-UuHA1h-Cf8", 518.0, "TANK VS COPS"),
    ("v_cruiseship", "OnWC__OxyTk", 186.5, "CRUISE SHIP MAYHEM"),
    ("v_subway", "BgO-5PVOj5c", 194.0, "SUBWAY SHOOTOUT"),
    ("v_sixstars", "ORYwlJXszi4", 112.0, "6 STARS"),
    ("v_beachbrawls", "gPCd2SD5X3k", 426.0, "BEACH BRAWL"),
    ("v_jasonlucia", "bfY0coYanSg", 289.0, "JASON & LUCIA"),
]
names = []
for slug, vid, t, hook in jobs:
    out = T / f"pro_{slug}_thumb.jpg"
    thumb.make(f"work/{vid}.mp4", hook, out, at=t, crop=C)
    names.append(out)
sheet = Image.new("RGB", (4 * 480, 2 * 270), "black")
for i, f in enumerate(names):
    sheet.paste(Image.open(f).resize((480, 270)), ((i % 4) * 480, (i // 4) * 270))
sheet.save("work/fl/thumbs_v_sheet.png")
print("thumbs done")
