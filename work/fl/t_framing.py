import sys
sys.path.insert(0, ".")
from clipx import framing
for vid, t0, t1 in [("6E2cBXFCDyQ", 355, 367), ("6E2cBXFCDyQ", 513, 528), ("9TLwyuGDSmI", 186, 204), ("gPCd2SD5X3k", 416, 438),
                    ("RSy0UkR0JBs", 181, 190)]:
    cam, W, H = framing.facecam(f"work/{vid}.mp4", t0, t1)
    print(vid, (t0, t1), "frame", (W, H), "facecam:", None if cam is None else tuple(round(v) for v in cam))
    if cam:
        cx, clear = framing.crop_cx_avoiding(cam, W, H, crop_w=H * 0.8 * 0.8, preferred=0.9)
        print("   crop shifted from 0.9 ->", round(cx, 3), "clear:", clear)
