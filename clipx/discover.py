"""Find source videos with the YouTube API (our version of GTA-Auto-Clipper's find_streams.py).

  python -m clipx.discover "GTA 6 fight" [--n 15] [--days 30] [--min-min 3] [--max-min 40] [--cc] [--live]

For every result it shows: views, length, channel, id, rights status (see clipx.rights), and whether it was a live stream
(chat replay exists, so clipx.signals can score its best moments). --cc keeps only YouTube Creative Commons videos,
the only licence YouTube can verify for you. Results are ordered by views (a popularity order, not a quality guarantee).
"""
import argparse
import datetime as dt
import re
from . import rights


def secs(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    h, mi, s = (int(g or 0) for g in m.groups()) if m else (0, 0, 0)
    return h * 3600 + mi * 60 + s


def search(query, n=15, days=30, min_min=3, max_min=40, cc=False, live=False):
    from .uploader import service
    yt = service()
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    kw = dict(q=query, part="id", type="video", order="viewCount", publishedAfter=since, maxResults=50, relevanceLanguage="en")
    if cc:
        kw["videoLicense"] = "creativeCommon"
    if live:
        kw["eventType"] = "live"
    ids = [i["id"]["videoId"] for i in yt.search().list(**kw).execute().get("items", [])]
    out = []
    for i in range(0, len(ids), 50):
        for x in yt.videos().list(part="snippet,statistics,contentDetails,liveStreamingDetails,status", id=",".join(ids[i:i + 50])).execute()["items"]:
            d = secs(x["contentDetails"]["duration"])
            if not live and not (min_min * 60 <= d <= max_min * 60):
                continue
            meta = {"channel": x["snippet"]["channelTitle"], "title": x["snippet"]["title"],
                    "license": "Creative Commons" if x["status"].get("license") == "creativeCommon" else None}
            status, why = rights.classify(meta)
            out.append({"id": x["id"], "views": int(x["statistics"].get("viewCount", 0)), "min": round(d / 60, 1),
                        "channel": meta["channel"], "title": meta["title"], "rights": status,
                        "was_live": "liveStreamingDetails" in x})
    return sorted(out, key=lambda r: -r["views"])[:n]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-min", type=float, default=3)
    ap.add_argument("--max-min", type=float, default=40)
    ap.add_argument("--cc", action="store_true")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    for r in search(a.query, a.n, a.days, a.min_min, a.max_min, a.cc, a.live):
        print(f"{r['views']:>10,} v {r['min']:>6}m  {r['rights']:<11}{'LIVE-CHAT ' if r['was_live'] else '          '}"
              f"{r['channel'][:20]:<20} {r['id']}  {r['title'][:60]}")
