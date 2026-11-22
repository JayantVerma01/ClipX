import json, datetime as dt
from clipx import uploader
yt = uploader.service()
# 1) my channel
me = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
print("MY CHANNEL:", me["snippet"]["title"], me["statistics"])
up = me["contentDetails"]["relatedPlaylists"]["uploads"]
ids = [i["contentDetails"]["videoId"] for i in yt.playlistItems().list(part="contentDetails", playlistId=up, maxResults=50).execute()["items"]]
for x in yt.videos().list(part="snippet,statistics", id=",".join(ids)).execute()["items"]:
    s = x["statistics"]; print(f"  {s.get('viewCount','0'):>6} v {s.get('likeCount','0'):>4} l  {x['snippet']['publishedAt'][:10]}  {x['snippet']['title'][:70]}")
# 2) breakout: views per subscriber on small channels
res = json.load(open("work/fl/research.json"))
cand = [z for k in ("short_vice","med_gta6","med_tips","short_gta6") for z in res[k]]
chids = {}
for z in cand:
    v = yt.videos().list(part="snippet", id=z["id"]).execute()["items"][0]; chids[z["id"]] = v["snippet"]["channelId"]
subs = {}
uc = list(set(chids.values()))
for i in range(0, len(uc), 50):
    for c in yt.channels().list(part="statistics", id=",".join(uc[i:i+50])).execute()["items"]:
        subs[c["id"]] = int(c["statistics"].get("subscriberCount", 0))
rows = []
for z in cand:
    sc = subs.get(chids[z["id"]], 0)
    if sc and sc < 300000: rows.append((z["views"]/max(sc,1), sc, z))
print("\nBREAKOUTS (small channels, <300k subs), views per subscriber:")
for r, sc, z in sorted(rows, key=lambda t: -t[0])[:14]:
    print(f"  {r:6.1f}x  {z['views']:>9,} views  {sc:>8,} subs  {z['dur']:<8} {z['ch'][:20]:<20} {z['title'][:70]}")
