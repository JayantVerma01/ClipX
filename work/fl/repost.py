"""Delete one posted video from YouTube and put its queue entry back to 'queued' so it can be uploaded again."""
import sys
from clipx import uploader

vid = sys.argv[1]
q = uploader.load()
it = next(x for x in q if x.get("video_id") == vid)
uploader.service().videos().delete(id=vid).execute()
print("deleted from YouTube:", vid, it["file"])
it.setdefault("deleted_ids", []).append(vid)
it["status"] = "queued"
for k in ("video_id", "posted_on", "uploaded_at"):
    it.pop(k, None)
uploader.save(q)
print("re-queued", it["file"])
