import datetime as dt, re
from clipx import uploader
yt = uploader.service()
since = (dt.datetime.utcnow() - dt.timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
def secs(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d); h, mi, s = (int(g or 0) for g in m.groups()); return h*3600+mi*60+s
qs = ["GTA 6 Lucia Jason kiss cutscene", "GTA 6 Lucia beach bikini", "GTA 6 romantic scene Jason Lucia", "GTA 6 Mandy Jason cutscene",
      "GTA 6 Lucia dancing club", "GTA 6 Lucia best moments", "GTA 6 date night Lucia Jason", "GTA 6 pool party yacht"]
seen = set()
for q in qs:
    r = yt.search().list(q=q, part="id", type="video", order="viewCount", publishedAfter=since, maxResults=10, relevanceLanguage="en").execute()
    ids = [i["id"]["videoId"] for i in r["items"] if i["id"]["videoId"] not in seen]
    if not ids: continue
    print("==", q)
    for x in sorted(yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()["items"], key=lambda x: -int(x["statistics"].get("viewCount", 0))):
        d = secs(x["contentDetails"]["duration"])
        if d < 120 or d > 2400: continue
        seen.add(x["id"])
        print(f"  {int(x['statistics'].get('viewCount',0)):>9,} {d//60:>3}m {x['snippet']['channelTitle'][:18]:<18} {x['id']} {x['snippet']['title'][:80]}")
