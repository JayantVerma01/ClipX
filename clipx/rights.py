"""Source-rights ledger: every source we clip gets a recorded status BEFORE anything is posted.

What GTA-Auto-Clipper does: nothing technical - it tells the user to hold the rights themselves ("creator credit does not
replace permission") and has the AI follow a 'standing source-rights policy' the user declares. We keep that principle but
add real checks:
  blocked      official publisher / trailer / press channel (Content ID will claim it)  -> posting refused
  cc           YouTube Creative Commons licence on the source video (detected via the API, not guessed)
  own / permission   set by you with proof (python -m clipx.rights mark <id> own --note "...")
  third-party  somebody's recording of the game: allowed with a warning, and goes through the quarantine check
Credit lines are generated for every source, but a credit is courtesy, not a licence.

  python -m clipx.rights check <url-or-id>      # inspect + record
  python -m clipx.rights mark <id> own|permission --note "email from creator, 2026-11-20"
  python -m clipx.rights list
"""
import argparse
import datetime as dt
import json
import shutil
import sys
from .config import ROOT, WORK
from .guard import RESTRICTED
import re

LEDGER = ROOT / "rights.json"


def _load():
    return json.loads(LEDGER.read_text(encoding="utf-8-sig")) if LEDGER.exists() else {}


def _save(d):
    LEDGER.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def classify(meta):
    """Pure logic (unit-tested). meta needs channel/title/license. Returns (status, reason)."""
    hay = f"{meta.get('channel') or ''} {meta.get('title') or ''}".lower()
    hit = [k for k in RESTRICTED if re.search(r"\b" + re.escape(k.strip()) + r"\b", hay)]
    if hit:
        return "blocked", f"looks like official publisher content ({', '.join(hit)}); Content ID blocks re-uploads"
    lic = str(meta.get("license") or "").lower()
    if "creative commons" in lic:
        return "cc", "YouTube Creative Commons licence (attribution required; Rockstar's game assets are still theirs)"
    return "third-party", "someone else's recording of the game: claim / 'reused content' risk, credit is not permission"


def inspect(url_or_id):
    """Fetch source info with yt-dlp (works for any site yt-dlp supports) and record it."""
    import yt_dlp
    url = url_or_id if "://" in url_or_id else f"https://www.youtube.com/watch?v={url_or_id}"
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    if not shutil.which("deno") and shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
    with yt_dlp.YoutubeDL(opts) as y:
        i = y.extract_info(url, download=False)
    meta = {"id": i["id"], "title": i.get("title"), "channel": i.get("channel") or i.get("uploader"), "url": url,
            "license": i.get("license"), "view_count": i.get("view_count")}
    return record(meta)


def record(meta, status=None, note=None):
    d = _load()
    auto, why = classify(meta)
    prev = d.get(meta["id"], {})
    keep_manual = prev.get("status") in ("own", "permission")      # a manual proof is never overwritten by auto-detection
    d[meta["id"]] = {"channel": meta.get("channel"), "title": meta.get("title"), "url": meta.get("url"),
                     "license": meta.get("license"),
                     "status": status or (prev["status"] if keep_manual else auto),
                     "reason": note or (prev.get("reason") if keep_manual else why),
                     "checked": dt.date.today().isoformat()}
    _save(d)
    return d[meta["id"]]


def status_of(vid):
    d = _load()
    if vid in d:
        return d[vid]
    mf = WORK / f"{vid}.meta.json"
    if mf.exists():
        try:
            return record(json.loads(mf.read_text(encoding="utf-8-sig")))
        except (ValueError, KeyError):
            pass
    return {"status": "third-party", "reason": "unrecorded source: treated as someone else's recording", "channel": None}


def gate(source_ids):
    """Pure-ish (unit-tested with a fake ledger). Returns (verdict, lines) with verdict in block / warn / ok."""
    verdict, lines = "ok", []
    for vid in source_ids or []:
        st = status_of(vid)
        s = st["status"]
        lines.append(f"{vid} ({st.get('channel')}): {s} - {st.get('reason')}")
        if s == "blocked":
            verdict = "block"
        elif s == "third-party" and verdict != "block":
            verdict = "warn"
    return verdict, lines


def credit_lines(source_ids):
    out = []
    for vid in source_ids or []:
        st = status_of(vid)
        out.append(f"{st.get('channel') or vid} - {st.get('url') or 'https://www.youtube.com/watch?v=' + vid}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "mark", "list"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("status", nargs="?", choices=["own", "permission"])
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    if a.cmd == "list":
        for k, v in _load().items():
            print(f"{v['status']:<12} {k:<13} {str(v.get('channel'))[:22]:<22} {v.get('reason')}")
    elif a.cmd == "check":
        r = inspect(a.target)
        print(json.dumps(r, indent=1, ensure_ascii=False))
    else:
        if not (a.target and a.status and a.note):
            sys.exit("usage: rights mark <id> own|permission --note '<proof: where the permission came from>'")
        meta = status_of(a.target)
        meta["id"] = a.target
        print(record(meta, status=a.status, note=a.note))


if __name__ == "__main__":
    main()
