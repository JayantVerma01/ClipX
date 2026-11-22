"""List what is taking space and which source videos are fully used. With 'delete': remove fully-used factory sources."""
import json
import sys
from pathlib import Path

R = Path(".")
F = R / "factory"
gb = lambda n: f"{n / 1e9:6.2f} GB"
size = lambda p: sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size

pending, total = {}, {}
for p in (F / "specs").glob("*.json"):
    src = Path(json.loads(p.read_text(encoding="utf-8"))["src"]).stem
    total[src] = total.get(src, 0) + 1
    d = F / "done" / p.stem
    if not (d.exists() and d.read_text().strip() in ("ok", "veto")):
        pending[src] = pending.get(src, 0) + 1
srcs = {s["id"] for s in json.loads((F / "sources.json").read_text(encoding="utf-8"))}
fed = set(json.loads((F / "fed.json").read_text(encoding="utf-8"))["done"])

used, busy, other = [], [], []
for v in sorted((R / "work").glob("*.mp4")):
    k = v.stem
    if k in total and not pending.get(k) and k in fed:
        used.append(v)
    elif k in total or k in srcs:
        busy.append(v)
    else:
        other.append(v)
print("factory sources fully used :", len(used), gb(sum(v.stat().st_size for v in used)))
print("factory sources still needed:", len(busy), gb(sum(v.stat().st_size for v in busy)))
print("other mp4 in work (older hand-built sources):", len(other), gb(sum(v.stat().st_size for v in other)))
for v in other:
    print("   ", v.name, gb(v.stat().st_size))
print("\nfolders:")
for d in sorted([p for p in R.iterdir() if p.is_dir()] + [p for p in (R / "other").iterdir() if p.is_dir()] + [p for p in F.iterdir() if p.is_dir()]
                + [p for p in (R / "work").iterdir() if p.is_dir()]):
    s = size(d)
    if s > 50e6:
        print(f"   {gb(s)}  {d}")
junk = [p for p in (R / "work").iterdir() if p.is_file() and p.suffix in (".part", ".ytdl", ".webm", ".m4a", ".wav", ".tmp")]
print("leftover partial/temp files in work:", len(junk), gb(sum(p.stat().st_size for p in junk)))

if "delete_old" in sys.argv:
    raw = [p for p in (R / "other" / "raw").iterdir() if p.is_file()]
    n = sum(p.stat().st_size for p in other + raw)
    for p in other + raw:
        p.unlink()
    print("deleted", len(other), "older sources +", len(raw), "raw cuts,", gb(n))

if "delete" in sys.argv:
    n = 0
    for v in used:
        n += v.stat().st_size
        v.unlink()
    print("deleted", len(used), "fully-used sources,", gb(n))
