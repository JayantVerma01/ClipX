import json, sys, yt_dlp
from pathlib import Path
W = Path("work")
IDS = ["gPCd2SD5X3k","8-DRGbQ1IXc","9TLwyuGDSmI","-UuHA1h-Cf8","6E2cBXFCDyQ","BgO-5PVOj5c","bfY0coYanSg","OnWC__OxyTk",
       "ORYwlJXszi4","DQqv-E4guu8","XwbiCpnZeRY","SzwQKzkG3bg","1GtrjKhSwzM"]
for vid in IDS:
    if (W / f"{vid}.mp4").exists(): continue
    opts = {"format": "bv*[height<=1080]+ba/b[height<=1080]", "merge_output_format": "mp4", "outtmpl": str(W / "%(id)s.%(ext)s"),
            "quiet": True, "noprogress": True, "continuedl": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            i = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
        (W / f"{vid}.meta.json").write_text(json.dumps({"id": vid, "title": i.get("title"), "channel": i.get("channel"),
            "url": f"https://www.youtube.com/watch?v={vid}", "duration": i.get("duration")}, indent=1), encoding="utf-8")
        print("ok", vid, i.get("title")[:60], flush=True)
    except Exception as e:
        print("FAIL", vid, str(e)[:120], flush=True)
print("DL DONE", flush=True)
