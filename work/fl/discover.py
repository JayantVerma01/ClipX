import json, datetime as dt
from clipx import uploader
yt = uploader.service()
since = (dt.datetime.utcnow() - dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
themes = {
 "fight": "GTA 6 fight gameplay", "stunt": "GTA 6 stunts crazy gameplay", "shootout": "GTA 6 shootout gunfight gameplay",
 "chase": "GTA 6 police chase wanted level", "heist": "GTA 6 robbery heist mission gameplay", "romance": "GTA 6 Lucia Jason romantic scene",
 "beach": "GTA 6 beach NPC", "nightclub": "GTA 6 nightclub strip club", "boat": "GTA 6 boat jetski helicopter",
 "physics": "GTA 6 physics ragdoll details", "mission": "GTA 6 mission walkthrough", "cc": "GTA 6 gameplay",
}
out = {}
for k, q in themes.items():
    for dur in (("medium", "long") if k != "cc" else ("medium",)):
        kw = dict(q=q, part="id", type="video", order="viewCount", publishedAfter=since, maxResults=12, videoDuration=dur, relevanceLanguage="en")
        if k == "cc": kw["videoLicense"] = "creativeCommon"
        try:
            r = yt.search().list(**kw).execute()
        except Exception as e:
            print(k, dur, "ERR", str(e)[:100]); continue
        ids = [i["id"]["videoId"] for i in r["items"]]
        if not ids: continue
        for x in yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()["items"]:
            s = x["statistics"]
            out.setdefault(k, []).append(dict(id=x["id"], title=x["snippet"]["title"], ch=x["snippet"]["channelTitle"],
                  views=int(s.get("viewCount", 0)), dur=x["contentDetails"]["duration"], pub=x["snippet"]["publishedAt"][:10]))
json.dump(out, open("work/fl/discover.json", "w"), indent=1)
import re
def secs(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d); h, mi, s = (int(g or 0) for g in m.groups()); return h*3600+mi*60+s
for k, v in out.items():
    print("==", k)
    seen = set()
    for z in sorted(v, key=lambda z: -z["views"]):
        if z["id"] in seen or secs(z["dur"]) > 3*3600: continue
        seen.add(z["id"])
        print(f"  {z['views']:>9,} {secs(z['dur'])//60:>4}m {z['ch'][:18]:<18} {z['id']} {z['title'][:75]}")
        if len(seen) >= 6: break
