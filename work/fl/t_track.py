import sys, time
sys.path.insert(0, ".")
from clipx import tracking
for vid, a, b in [("bfY0coYanSg", 60, 72), ("sPdTmBcXkas", 650, 662), ("9TLwyuGDSmI", 186, 198), ("OnWC__OxyTk", 176, 188)]:
    t = time.time()
    k = tracking.track(f"work/{vid}.mp4", a, b)
    print(vid, (a, b), "->", None if k is None else [(round(x, 1), round(c, 2)) for x, c in k][:12], f"({time.time()-t:.1f}s)")
