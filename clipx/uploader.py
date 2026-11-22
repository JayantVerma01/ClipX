"""YouTube upload queue with SAFE publishing.

Old behaviour: upload public straight away -> a copyright block (like your first Short) was live and visible.
New default (inspired by GTA-Auto-Clipper's review gate / dry-run / idempotency, but free and built on the YouTube API):
  1. post     uploads PRIVATE (quarantine). Nothing is public yet.
  2. release  after YouTube has processed + copyright-checked it, reads the video's status:
                clean   -> made public (or left scheduled)
                blocked -> stays private, flagged (rejection reason / blocked in all regions)
  3. health   re-checks everything already posted (views, region blocks, rejections)
Scheduling: `schedule` uploads private with a publishAt time, so YouTube publishes it even while your PC is off
(GTA-Auto-Clipper needs the paid Zernio service for that).

  python -m clipx.uploader auth | status | pause | resume
  python -m clipx.uploader post [--n 1] [--dry-run] [--direct] [--publish-at 2026-11-21T12:00:00+05:30]
  python -m clipx.uploader release [--hold-minutes 10] [--force]
  python -m clipx.uploader schedule --times 12:00,17:00,21:00 [--start 2026-11-21] [--n 6]
  python -m clipx.uploader health
YouTube API quota: one upload costs ~1600 of the 10,000 daily units -> about 6 uploads a day at most.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from .config import ROOT, OUT, POSTED, AUX

SECRETS = ROOT / "secrets"
QUEUE = ROOT / "queue.json"
DAILY_LIMIT = 6
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
PAUSE_FLAG = ROOT / "PAUSED"
UPLOAD_STATES = ("quarantine", "scheduled", "posted")        # statuses that mean "a video exists on YouTube"


def load():
    return json.loads(QUEUE.read_text(encoding="utf-8-sig")) if QUEUE.exists() else []


def save(q):
    QUEUE.write_text(json.dumps(q, indent=1), encoding="utf-8")


def enqueue(item):
    q = load()
    if not any(x["file"] == item["file"] for x in q):
        q.append({**item, "status": "queued"})
        save(q)


def enqueue_pro(slug, title, description, tags, thumb=None, kind=None, extra_credit=True):
    """Queue a clip made by clipx.pro: sources and credit lines come from its provenance sidecar (other/meta)."""
    from . import rights
    meta = json.loads((AUX / "meta" / f"pro_{slug}.json").read_text(encoding="utf-8"))
    ids = [s["id"] for s in meta["sources"]]
    desc = description
    if extra_credit:
        desc += "\n\nSource footage: " + " | ".join(rights.credit_lines(ids))
    enqueue({"file": meta["file"], "kind": kind or meta.get("kind") or "short", "title": title, "description": desc,
             "tags": tags, "thumb": thumb, "sources": ids})


def service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    tok = SECRETS / "token.json"
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS / "client_secret.json"), SCOPES)
            creds = flow.run_local_server(port=8085, open_browser=True,
                                          authorization_prompt_message="OPEN THIS URL: {url}", timeout_seconds=600)
        tok.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def _thumb_path(name):
    for d in (AUX / "thumbs", AUX, OUT):
        if (d / name).exists():
            return d / name
    return OUT / name


def file_sha(path):
    """Cheap content fingerprint (size + first/last 4 MB) so the same clip is never uploaded twice under two names."""
    p = Path(path)
    h = hashlib.sha1(str(p.stat().st_size).encode())
    with p.open("rb") as f:
        h.update(f.read(4 << 20))
        f.seek(max(0, p.stat().st_size - (4 << 20)))
        h.update(f.read())
    return h.hexdigest()


def to_utc_rfc3339(when):
    """'2026-11-21T12:00:00+05:30' -> '2026-11-21T06:30:00Z' (pure, unit-tested)."""
    d = dt.datetime.fromisoformat(when)
    if d.tzinfo is None:
        d = d.replace(tzinfo=IST)
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upload(yt, it, privacy="private", publish_at=None):
    from googleapiclient.http import MediaFileUpload
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if publish_at:
        status["privacyStatus"] = "private"              # YouTube requires private + publishAt for scheduling
        status["publishAt"] = to_utc_rfc3339(publish_at)
    body = {"snippet": {"title": it["title"][:100], "description": it["description"], "tags": it["tags"],
                        "categoryId": "20"}, "status": status}
    src = POSTED / it["file"] if (POSTED / it["file"]).exists() and not (OUT / it["file"]).exists() else OUT / it["file"]
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(src), chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    if it.get("thumb"):
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(_thumb_path(it["thumb"])))).execute()
        except Exception as e:
            print("  thumbnail not set (channel may need phone verification):", str(e)[:120])
    return vid


def assess(res):
    """Pure logic (unit-tested). res = a YouTube videos.list item (status, contentDetails, processingDetails).
    Returns (state, reason) with state in clean / pending / restricted / blocked."""
    st = res.get("status", {})
    cd = res.get("contentDetails", {})
    pd = res.get("processingDetails", {})
    upload_status = st.get("uploadStatus")
    if upload_status in ("rejected", "failed", "deleted"):
        why = st.get("rejectionReason") or st.get("failureReason") or upload_status
        return "blocked", f"upload {upload_status}: {why}"
    rr = cd.get("regionRestriction")
    if rr is not None:
        if "allowed" in rr and not rr["allowed"]:
            return "blocked", "blocked in every country (copyright claim / policy)"
        if rr.get("blocked"):
            return "restricted", f"blocked in {len(rr['blocked'])} countries: {', '.join(rr['blocked'][:6])}"
    if pd.get("processingStatus") in ("processing",) or upload_status == "uploaded":
        return "pending", "YouTube is still processing / checking the video"
    if pd.get("processingStatus") in ("failed", "terminated"):
        return "blocked", f"processing {pd.get('processingStatus')}"
    return "clean", "processed, no region block, no rejection"


def _fetch(yt, ids):
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="status,contentDetails,processingDetails,statistics", id=",".join(ids[i:i + 50])).execute()
        for x in r.get("items", []):
            out[x["id"]] = x
    return out


def _move_to_posted(it):
    src = OUT / it["file"]
    if src.exists():
        POSTED.mkdir(exist_ok=True)
        src.replace(POSTED / it["file"])


def post(n=1, dry=False, direct=False, publish_at=None, accept_risk=False):
    if PAUSE_FLAG.exists():
        print("QUEUE IS PAUSED (" + PAUSE_FLAG.read_text(encoding="utf-8").strip() + "). "
              "Run `python -m clipx.uploader resume` to enable posting.")
        return
    from . import rights
    q = load()
    today = dt.date.today().isoformat()
    done_today = sum(1 for x in q if x["status"] in UPLOAD_STATES and x.get("posted_on") == today)
    room = max(0, min(n, DAILY_LIMIT - done_today))
    todo = [x for x in q if x["status"] == "queued"][:room]
    if not todo:
        print(f"nothing to post (uploaded today: {done_today}/{DAILY_LIMIT}, queued: {sum(x['status']=='queued' for x in q)})")
        return
    yt = None if dry else service()
    for it in todo:
        verdict, lines = rights.gate(it.get("sources"))
        for ln in lines:
            print("   rights:", ln)
        if verdict == "block" and not accept_risk:
            print(f"REFUSED {it['file']}: a source is official publisher content. Use --i-have-rights only with real permission.")
            it["status"] = "held"
            it["hold_reason"] = "rights: blocked source"
            save(q)
            continue
        path = OUT / it["file"]
        if not path.exists() and not (POSTED / it["file"]).exists():
            print(f"missing file {it['file']}, skipping")
            continue
        sha = file_sha(path if path.exists() else POSTED / it["file"])
        dup = next((x for x in q if x is not it and x.get("sha") == sha and x["status"] in UPLOAD_STATES), None)
        if dup:
            print(f"SKIPPED {it['file']}: identical to already-uploaded {dup['file']} (video {dup.get('video_id')})")
            it["status"], it["hold_reason"] = "held", f"duplicate of {dup['file']}"
            save(q)
            continue
        mode = "DIRECT PUBLIC" if direct and not publish_at else ("SCHEDULED" if publish_at else "PRIVATE quarantine")
        print(("DRY RUN: would upload " if dry else "uploading ") + f"{it['file']}  ->  {it['title']}   [{mode}]")
        if dry:
            continue
        it["sha"] = sha
        it["video_id"] = upload(yt, it, "public" if direct and not publish_at else "private", publish_at)
        it["posted_on"], it["uploaded_at"] = today, dt.datetime.now().isoformat(timespec="seconds")
        if publish_at:
            it["status"], it["publish_at"] = "scheduled", publish_at
        elif direct:
            it["status"] = "posted"
        else:
            it["status"] = "quarantine"
        save(q)
        _move_to_posted(it)
        print(f"  https://youtube.com/watch?v={it['video_id']}  ({it['status']})")
    if not dry and any(x["status"] == "quarantine" for x in q):
        print("Uploaded privately. Run `python -m clipx.uploader release` in ~10 minutes to publish the clean ones.")


def release(hold_minutes=10, force=False):
    """Publish quarantined clips that YouTube has processed without blocking them; flag the rest."""
    q = load()
    waiting = [x for x in q if x["status"] in ("quarantine", "scheduled") and x.get("video_id")]
    if not waiting:
        print("nothing in quarantine")
        return
    yt = service()
    res = _fetch(yt, [x["video_id"] for x in waiting])
    now = dt.datetime.now()
    for it in waiting:
        age = (now - dt.datetime.fromisoformat(it["uploaded_at"])).total_seconds() / 60 if it.get("uploaded_at") else 999
        r = res.get(it["video_id"])
        if r is None:
            print(f"? {it['file']}: video {it['video_id']} not found on YouTube (deleted?)")
            it["status"], it["hold_reason"] = "held", "video missing on YouTube"
            continue
        state, why = assess(r)
        if state == "clean" and age < hold_minutes and not force:
            print(f"... {it['file']}: looks clean but only {age:.0f} min old; waiting until {hold_minutes} min so Content ID can finish")
            continue
        if state == "pending":
            print(f"... {it['file']}: {why}")
            continue
        if state == "blocked":
            print(f"BLOCKED {it['file']}: {why}")
            it["status"], it["block_reason"] = "blocked", why
            if it.get("publish_at"):                       # cancel the schedule so it never goes live
                yt.videos().update(part="status", body={"id": it["video_id"], "status": {
                    "privacyStatus": "private", "selfDeclaredMadeForKids": False}}).execute()
            continue
        if it["status"] == "scheduled":
            print(f"OK scheduled {it['file']}: {state} ({why}); goes live {it['publish_at']}")
            continue
        yt.videos().update(part="status", body={"id": it["video_id"], "status": {
            "privacyStatus": "public", "selfDeclaredMadeForKids": False}}).execute()
        it["status"] = "posted"
        print(f"PUBLISHED {it['file']}  https://youtube.com/watch?v={it['video_id']}" + ("  (" + why + ")" if state == "restricted" else ""))
    save(q)


def health():
    """Re-check every uploaded video: views, rejections, region blocks."""
    q = load()
    items = [x for x in q if x.get("video_id") and x["status"] in UPLOAD_STATES + ("blocked",)]
    if not items:
        print("no uploaded videos yet")
        return
    res = _fetch(service(), [x["video_id"] for x in items])
    for it in items:
        r = res.get(it["video_id"])
        if not r:
            print(f"MISSING  {it['video_id']}  {it['file']}")
            continue
        state, why = assess(r)
        views = r.get("statistics", {}).get("viewCount", "?")
        priv = r.get("status", {}).get("privacyStatus")
        flag = "" if state in ("clean", "pending") else "  <<<<"
        print(f"{state.upper():<10} {priv:<8} {views:>7} views  {it['video_id']}  {it['file']}{flag}" + ("" if state == "clean" else f"  [{why}]"))
        if state == "blocked" and it["status"] != "blocked":
            it["status"], it["block_reason"] = "blocked", why
    save(q)


def schedule(times, start=None, n=6):
    """Assign publish times to the next queued clips: `times` like ['12:00','17:00','21:00'] (IST), starting `start`."""
    q = load()
    today = dt.date.today().isoformat()
    done_today = sum(1 for x in q if x["status"] in UPLOAD_STATES and x.get("posted_on") == today)
    n = max(0, min(n, DAILY_LIMIT - done_today))
    todo = [x for x in q if x["status"] == "queued"][:n]
    day = dt.date.fromisoformat(start) if start else dt.date.today() + dt.timedelta(days=1)
    slots, d = [], day
    while len(slots) < len(todo):
        for t in times:
            hh, mm = [int(v) for v in t.split(":")]
            slots.append(dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=IST).isoformat())
        d += dt.timedelta(days=1)
    for it, when in zip(todo, slots):
        print(f"scheduling {it['file']} for {when}")
        yt = service()
        sha = file_sha(OUT / it["file"]) if (OUT / it["file"]).exists() else file_sha(POSTED / it["file"])
        it["sha"] = sha
        it["video_id"] = upload(yt, it, "private", when)
        it["status"], it["publish_at"] = "scheduled", when
        it["posted_on"], it["uploaded_at"] = today, dt.datetime.now().isoformat(timespec="seconds")
        save(q)
        _move_to_posted(it)
        print(f"  https://youtube.com/watch?v={it['video_id']}  scheduled {when}")
    print("Run `python -m clipx.uploader release` later to verify the scheduled uploads were not blocked.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["auth", "status", "post", "pause", "resume", "release", "health", "schedule"])
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--direct", action="store_true", help="upload public immediately (old behaviour, no safety check)")
    ap.add_argument("--publish-at", default=None, help="ISO time with offset, e.g. 2026-11-21T12:00:00+05:30")
    ap.add_argument("--hold-minutes", type=int, default=10)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--times", default="12:00,17:00,21:00")
    ap.add_argument("--start", default=None)
    ap.add_argument("--i-have-rights", action="store_true")
    a = ap.parse_args()
    if a.cmd == "auth":
        service()
        print("authorised; token saved")
    elif a.cmd == "pause":
        PAUSE_FLAG.write_text("paused by user", encoding="utf-8")
        print("posting paused")
    elif a.cmd == "resume":
        PAUSE_FLAG.unlink(missing_ok=True)
        print("posting resumed")
    elif a.cmd == "status":
        print("PAUSED" if PAUSE_FLAG.exists() else "active")
        for x in load():
            extra = x.get("block_reason") or x.get("hold_reason") or x.get("publish_at") or ""
            print(x["status"].ljust(10), x["kind"].ljust(5), x["file"], "|", x["title"], ("  [" + extra + "]") if extra else "")
    elif a.cmd == "release":
        release(a.hold_minutes, a.force)
    elif a.cmd == "health":
        health()
    elif a.cmd == "schedule":
        schedule(a.times.split(","), a.start, a.n)
    else:
        post(a.n, a.dry_run, a.direct, a.publish_at, a.i_have_rights)
