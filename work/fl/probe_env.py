import json, sys
try:
    import onnxruntime
    print("onnxruntime", onnxruntime.__version__)
except Exception as e:
    print("onnxruntime missing:", type(e).__name__)
import cv2
print("cv2", cv2.__version__, "FaceDetectorYN" , hasattr(cv2, "FaceDetectorYN"))
import yt_dlp
ids = sys.argv[1:] or ["9TLwyuGDSmI", "8-DRGbQ1IXc", "wiW1mpHZb_Y"]
for vid in ids:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "js_runtimes": {"node": {}}}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            i = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        hm = i.get("heatmap")
        print(vid, "| license:", i.get("license"), "| heatmap:", (len(hm) if hm else None), "| views:", i.get("view_count"),
              "| was_live:", i.get("was_live"), "| subs-langs:", [k for k in (i.get("subtitles") or {})][:3],
              "| live_chat sub:", "live_chat" in (i.get("subtitles") or {}))
        if hm:
            top = sorted(hm, key=lambda h: -h["value"])[:3]
            print("   top replayed:", [(round(h["start_time"]), round(h["value"], 2)) for h in top])
    except Exception as e:
        print(vid, "ERR", str(e)[:160])
