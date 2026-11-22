import sys
sys.path.insert(0, ".")
from pathlib import Path
from clipx import thumb
T = Path("other/thumbs"); T.mkdir(parents=True, exist_ok=True)
jobs = [
    ("sens_vcafterdark", "work/ID-C0E_DidA.mp4", 127.0, "VICE CITY AFTER DARK", (0.08, 0.05, 0.92, 0.84)),
    ("sens_dancefloor", "work/RSy0UkR0JBs.mp4", 198.5, "STEAMY DANCE FLOOR", (0.08, 0.06, 0.92, 0.84)),
    ("sens_firstnight", "work/ID-C0E_DidA.mp4", 153.5, "FIRST NIGHT", (0.08, 0.05, 0.92, 0.84)),
    ("sens_nightclub", "work/RSy0UkR0JBs.mp4", 213.5, "AFTER DARK", (0.05, 0.05, 0.95, 0.84)),
    ("sens_yacht", "work/boNEXq35Hg0.mp4", 303.5, "GOLDEN HOUR", (0.05, 0.05, 0.95, 0.84)),
]
for slug, src, t, hook, crop in jobs:
    thumb.make(src, hook, T / f"pro_{slug}_thumb.jpg", at=t, crop=crop)
    print("thumb", slug)
