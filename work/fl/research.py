import json, datetime as dt, sys
from clipx import uploader
yt = uploader.service()
since = (dt.datetime.utcnow() - dt.timedelta(days=int(sys.argv[1]))).strftime("%Y-%m-%dT%H:%M:%SZ")
def run(q, dur, order="viewCount", n=25):
    r = yt.search().list(q=q, part="id", type="video", order=order, publishedAfter=since, maxResults=n, videoDuration=dur, relevanceLanguage="en").execute()
    ids = [i["id"]["videoId"] for i in r["items"]]
    v = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()["items"]
    out = []
    for x in v:
        s = x["statistics"]; d = x["contentDetails"]["duration"]
        out.append(dict(id=x["id"], title=x["snippet"]["title"], ch=x["snippet"]["channelTitle"], pub=x["snippet"]["publishedAt"][:10],
                        views=int(s.get("viewCount", 0)), likes=int(s.get("likeCount", 0)), com=int(s.get("commentCount", 0)), dur=d))
    return sorted(out, key=lambda z: -z["views"])
res = {}
for label, q, dur in [("short_gta6","GTA 6 #shorts","short"),("short_vice","GTA 6 Vice City","short"),("med_gta6","GTA 6 gameplay","medium"),("long_gta6","GTA 6","long"),("med_tips","GTA 6 tips and tricks","medium")]:
    res[label] = run(q, dur)
json.dump(res, open("work/fl/research.json","w"), indent=1)
for k, v in res.items():
    print("==", k)
    for z in v[:10]:
        print(f"{z['views']:>10,} v {z['likes']:>8,} l {z['com']:>6,} c  {z['dur']:<9} {z['pub']} {z['ch'][:22]:<22} {z['title'][:80]}")
