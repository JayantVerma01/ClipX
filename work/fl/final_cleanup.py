"""After every planned clip is rendered: empty work\\ except the credit files (*.meta.json) and the scripts in work\\fl.
Add the word 'other' to also clear render leftovers and rejected clips from other\\ (keeps other\\meta, other\\thumbs, other\\qa).
Does nothing (exit 3) while any clip is still waiting to render."""
import shutil
import sys
from pathlib import Path

F = Path("factory")
pending = [p.stem for p in (F / "specs").glob("*.json") if not (F / "done" / p.stem).exists()]
if pending or any((F / "lock").iterdir()):
    print("not finished:", len(pending), "clips still to render")
    sys.exit(3)

freed = 0


def rm(p):
    global freed
    if p.is_dir():
        freed += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        shutil.rmtree(p, ignore_errors=True)
    elif p.exists():
        freed += p.stat().st_size
        p.unlink()


W = Path("work")
for p in W.iterdir():
    if p.name == "fl" or p.name.endswith(".meta.json"):
        continue
    rm(p)
for p in (W / "fl").iterdir():
    if p.suffix.lower() in (".png", ".jpg"):
        rm(p)
if "other" in sys.argv:
    O = Path("other")
    for p in O.iterdir():
        if p.is_file() and (p.name.endswith(".ass") or p.name.endswith(".filter.txt") or p.name.endswith(".sfx.wav")):
            rm(p)
    for p in (O / "rejected").iterdir():
        rm(p)
print(f"cleanup done, freed {freed / 1e9:.2f} GB")
