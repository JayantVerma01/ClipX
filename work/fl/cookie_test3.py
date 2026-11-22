import shutil
import yt_dlp
CK = "secrets/youtube_cookies.txt"
VID = "4ksv4fJqvCI"
variants = {
    "default": {},
    "ejs-github": {"remote_components": ["ejs:github"]},
    "tv": {"extractor_args": {"youtube": {"player_client": ["tv"]}}},
    "tv+ejs": {"extractor_args": {"youtube": {"player_client": ["tv"]}}, "remote_components": ["ejs:github"]},
    "web_safari": {"extractor_args": {"youtube": {"player_client": ["web_safari"]}}},
    "mweb": {"extractor_args": {"youtube": {"player_client": ["mweb"]}}},
    "tv_embedded": {"extractor_args": {"youtube": {"player_client": ["tv_embedded"]}}},
    "android_vr-nocookie": {"extractor_args": {"youtube": {"player_client": ["android_vr"]}}, "_nocookie": True},
}
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
        print(f"{name:<20} video formats: {len(fm):>3}  max height: {hs[-1] if hs else None}", flush=True)
    except Exception as e:
        print(f"{name:<20} FAILED: {str(e)[:110].encode('ascii', 'replace').decode()}", flush=True)
