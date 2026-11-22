import shutil
import yt_dlp
CK = "secrets/youtube_cookies.txt"
VID = "z36_OFTtKtE"
variants = {
    "tv_embedded+cookies": {"extractor_args": {"youtube": {"player_client": ["tv_embedded"]}}},
    "default+cookies": {},
    "tv+cookies": {"extractor_args": {"youtube": {"player_client": ["tv"]}}},
    "web_safari+cookies": {"extractor_args": {"youtube": {"player_client": ["web_safari"]}}},
    "mweb+cookies": {"extractor_args": {"youtube": {"player_client": ["mweb"]}}},
    "default-nocookie": {"_nocookie": True},
    "android_vr-nocookie": {"extractor_args": {"youtube": {"player_client": ["android_vr"]}}, "_nocookie": True},
    "tv_embedded-nocookie": {"extractor_args": {"youtube": {"player_client": ["tv_embedded"]}}, "_nocookie": True},
}
print("yt-dlp", yt_dlp.version.__version__)
for name, extra in variants.items():
    extra = dict(extra)
    nocookie = extra.pop("_nocookie", False)
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "ignore_no_formats_error": True, **extra}
    if not nocookie:
        opts["cookiefile"] = CK
    if not shutil.which("deno") and shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            i = y.extract_info(f"https://www.youtube.com/watch?v={VID}", download=False)
        fm = [f for f in (i.get("formats") or []) if f.get("vcodec") not in (None, "none")]
        hs = sorted({f.get("height") for f in fm if f.get("height")})
        print(f"{name:<22} video formats: {len(fm):>3}  max height: {hs[-1] if hs else None}", flush=True)
    except Exception as e:
        print(f"{name:<22} FAILED: {str(e)[:100].encode('ascii', 'replace').decode()}", flush=True)
