import shutil
import yt_dlp
VID = "4ksv4fJqvCI"
for br in ("firefox", "edge", "chrome", "brave"):
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "cookiesfrombrowser": (br,)}
    if not shutil.which("deno") and shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            i = y.extract_info(f"https://www.youtube.com/watch?v={VID}", download=False)
        print(br, "OK ->", (i.get("title") or "")[:40].encode("ascii", "replace").decode(), "| formats", len(i.get("formats") or []))
    except Exception as e:
        print(br, "FAILED:", str(e)[:150].encode("ascii", "replace").decode())
