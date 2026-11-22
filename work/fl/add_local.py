"""Write the credit meta file for a hand-supplied source, then (with 'refeed') put it back in the feed queue."""
import json
import sys
from pathlib import Path

VID = "ejIdp8axfhY"
src = next(s for s in json.loads(Path("factory/sources.json").read_text(encoding="utf-8")) if s["id"] == VID)
print({k: str(v).encode("ascii", "replace").decode() for k, v in src.items()})
meta = Path(f"work/{VID}.meta.json")
if not meta.exists():
    meta.write_text(json.dumps({"id": VID, "title": src.get("title", ""), "channel": src.get("channel", ""),
                                "url": f"https://www.youtube.com/watch?v={VID}", "duration": 1935},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("meta written")
if "refeed" in sys.argv:
    p = Path("factory/fed.json")
    s = json.loads(p.read_text(encoding="utf-8"))
    s["done"] = [x for x in s["done"] if x != VID]
    s["failed"] = [x for x in s.get("failed", []) if x != VID]
    p.write_text(json.dumps(s), encoding="utf-8")
    Path("factory/FEED_DONE").unlink(missing_ok=True)
    print("re-queued")
