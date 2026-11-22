"""Schedule the next finished factory Shorts on YouTube: 2 a day at 11:00 and 17:00 IST.

  python work\\fl\\sched_next.py pick 2     # show which Shorts would go next (no upload)
  python work\\fl\\sched_next.py go 2       # upload them privately with a publish time
Order: one theme after another in rotation, so the same kind of clip never runs for days.
"""
import datetime as dt
import json
import sys
from pathlib import Path
from clipx import uploader

F = Path("factory")
TIMES = ["11:00", "17:00"]


def candidates():
    q = uploader.load()
    used = {x["file"] for x in q}
    by = {}
    for d in sorted((F / "done").iterdir()):
        s = d.name
        if "_v" in s[-4:] or d.read_text().strip() != "ok":
            continue
        if f"pro_{s}.mp4" in used or not Path(f"output/pro_{s}.mp4").exists():
            continue
        by.setdefault(s.split("_")[1], []).append(s)
    for th in by:
        by[th].sort(key=lambda s: int(s.rsplit("_s", 1)[1]))
    # rotation continues from the last scheduled factory Short's theme
    themes = sorted(by)
    last = next((x["file"].split("_")[2] for x in reversed(q) if x["file"].startswith("pro_f_")), None)
    if last in themes:
        i = themes.index(last) + 1
        themes = themes[i:] + themes[:i]
    out = []
    while any(by.values()):
        for th in themes:
            if by.get(th):
                out.append(by[th].pop(0))
    return out


def next_day():
    q = uploader.load()
    days = [x["publish_at"][:10] for x in q if x.get("publish_at")]
    tomorrow = dt.date.today() + dt.timedelta(days=1)
    return max(tomorrow, dt.date.fromisoformat(max(days)) + dt.timedelta(days=1)) if days else tomorrow


def _slots():
    """11:00 and 17:00 IST, day after day, starting with any slot still at least 2 hours away today."""
    now = dt.datetime.now(uploader.IST)
    d = now.date()
    while True:
        for t in TIMES:
            hh, mm = [int(v) for v in t.split(":")]
            s = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=uploader.IST)
            if s > now + dt.timedelta(hours=2):
                yield s.isoformat()
        d += dt.timedelta(days=1)


def auto():
    """Daily run: fill today's upload allowance (6) with the next Shorts, then check nothing scheduled got blocked.
    Returns how many uploads are still owed today (0 = finished for today)."""
    q = uploader.load()
    today = dt.date.today().isoformat()
    done = sum(1 for x in q if x["status"] in uploader.UPLOAD_STATES and x.get("posted_on") == today)
    room = uploader.DAILY_LIMIT - done
    waiting = [x for x in q if x["status"] == "queued"]
    if waiting and any(x.get("kind") != "short" for x in waiting):
        print("queue holds something that is not a Short; not touching it")
        return 0
    if room > 0:
        c = candidates()
        for s in c[:max(0, room - len(waiting))]:
            m = json.loads((F / "meta" / f"{s}.json").read_text(encoding="utf-8"))
            uploader.enqueue_pro(s, m["title"], m["description"], m["tags"], thumb=None, kind="short")
        try:
            q = uploader.load()
            taken = {x["publish_at"] for x in q if x.get("publish_at") and x["status"] in uploader.UPLOAD_STATES}
            yt = uploader.service()
            for it in [x for x in q if x["status"] == "queued"][:room]:
                when = next(s for s in _slots() if s not in taken)          # earliest free 11:00 / 17:00, never a gap
                src = uploader.OUT / it["file"]
                it["sha"] = uploader.file_sha(src if src.exists() else uploader.POSTED / it["file"])
                print(f"scheduling {it['file']} for {when}")
                it["video_id"] = uploader.upload(yt, it, "private", when)
                it["status"], it["publish_at"] = "scheduled", when
                it["posted_on"], it["uploaded_at"] = today, dt.datetime.now().isoformat(timespec="seconds")
                taken.add(when)
                uploader.save(q)
                uploader._move_to_posted(it)
        except Exception as e:                       # no internet / quota used up / sign-in expired: try again later
            print("upload stopped:", str(e)[:200].encode("ascii", "replace").decode())
    try:
        uploader.release()
    except Exception as e:
        print("block-check failed:", str(e)[:120].encode("ascii", "replace").decode())
    q = uploader.load()
    done = sum(1 for x in q if x["status"] in uploader.UPLOAD_STATES and x.get("posted_on") == today)
    last = max((x["publish_at"][:10] for x in q if x.get("publish_at")), default="-")
    left = len(candidates())
    print(f"SUMMARY {dt.datetime.now():%Y-%m-%d %H:%M} uploaded today {done}/{uploader.DAILY_LIMIT} | scheduled through {last} | "
          f"blocked {sum(x['status'] == 'blocked' for x in q)} | Shorts still to schedule {left}")
    return 0 if left == 0 else max(0, uploader.DAILY_LIMIT - done)


if __name__ == "__main__":
    if sys.argv[1] == "auto":
        sys.exit(10 if auto() else 0)
    mode, n = sys.argv[1], int(sys.argv[2])
    n -= n % 2                                   # whole days only
    c = candidates()
    print("finished Shorts not yet scheduled:", len(c), "| next free day:", next_day())
    pick = c[:n]
    for s in pick:
        m = json.loads((F / "meta" / f"{s}.json").read_text(encoding="utf-8"))
        print("  ", s, "|", m["title"])
    if mode == "go" and pick:
        start = next_day().isoformat()
        for s in pick:
            m = json.loads((F / "meta" / f"{s}.json").read_text(encoding="utf-8"))
            uploader.enqueue_pro(s, m["title"], m["description"], m["tags"], thumb=None, kind="short")
        uploader.schedule(TIMES, start=start, n=len(pick))
