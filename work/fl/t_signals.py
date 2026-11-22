import sys
sys.path.insert(0, ".")
from clipx import signals
for vid, dur in [("9TLwyuGDSmI", 540), ("dQw4w9WgXcQ", 213)]:
    arr, used = signals.fetch(vid, dur, force=True)
    print(vid, "->", used, None if arr is None else (len(arr), round(float(arr.max()), 2), int((arr > 2).sum()), "seconds above 2"))
