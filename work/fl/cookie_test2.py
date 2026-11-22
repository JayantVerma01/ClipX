import shutil
from pathlib import Path
import yt_dlp
ck = Path("secrets/youtube_cookies.txt")
print("file exists:", ck.exists(), "| size:", ck.stat().st_size if ck.exists() else 0)
if ck.exists():
    lines = ck.read_text(encoding="utf-8", errors="replace").splitlines()
    yt = [l for l in lines if l and not l.startswith("#") and "youtube.com" in l.split("\t")[0]]
    names = {l.split("\t")[5] for l in yt if len(l.split("\t")) >= 7}
    print("netscape header:", lines[0].startswith("# Netscape") or lines[0].startswith("# HTTP Cookie"), "| youtube cookies:", len(yt),
          "| signed-in cookies present:", bool(names & {"SID", "__Secure-1PSID", "__Secure-3PSID", "LOGIN_INFO"}))
    for vid in ("4ksv4fJqvCI", "fCofR6iJ3ZA"):
        opts = {"quiet": True, "no_warnings": True, "skip_download": True, "cookiefile": str(ck)}
        if not shutil.which("deno") and shutil.which("node"):
            opts["js_runtimes"] = {"node": {}}
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                i = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            hs = sorted({f.get("height") for f in i.get("formats", []) if f.get("height")})
            print(vid, "OK | formats:", len(i.get("formats", [])), "| max height:", hs[-1] if hs else None)
        except Exception as e:
            print(vid, "FAILED:", str(e)[:170].encode("ascii", "replace").decode())
