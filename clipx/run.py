"""ONE command: link or file in -> edited Shorts/videos + thumbnails + titles in the upload queue.
  python -m clipx.run <youtube-url-or-file> [--kind short|video|both] [--max N] [--no-queue]
Nothing is uploaded here; `python -m clipx.uploader post` does that (max 3/day).
"""
import argparse
import json
from pathlib import Path
from .config import OUT, RAW, AUX, WORK, MAX_CLIPS_PER_SOURCE
from . import cli, meta, style_pro, edit, thumb, uploader


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--kind", choices=["short", "video", "both"], default="both")
    ap.add_argument("--max", type=int, default=MAX_CLIPS_PER_SOURCE)
    ap.add_argument("--no-queue", action="store_true")
    ap.add_argument("--i-have-rights", action="store_true", help="skip the official-publisher copyright warning")
    ap.add_argument("--style", choices=["max", "pro", "classic"], default="max", help="edit style (default: max)")
    ap.add_argument("--game", choices=list(meta.GAMES), default="gta6", help="which game the footage is from")
    ap.add_argument("--tag", default=None, help="top-left chip text (default: the game's name)")
    ap.add_argument("--lang", default="en", help="en (default, fast) | auto (detect; Hindi -> Hinglish captions) | hi")
    ap.add_argument("--no-signals", action="store_true", help="skip chat-replay / most-replayed scoring")
    a = ap.parse_args()

    mp = cli.process(a.src, a.kind, a.max, a.i_have_rights, a.lang, not a.no_signals)
    vid = mp.stem.replace(".manifest", "")
    entries = json.loads(mp.read_text(encoding="utf-8-sig"))
    mj = WORK / f"{vid}.meta.json"
    source = None
    if mj.exists():
        m = json.loads(mj.read_text(encoding="utf-8"))
        source = f"{m.get('channel')} - {m.get('url')}" if m.get("channel") else m.get("url")

    for i, e in enumerate(entries):
        md = meta.make(e, i, source, a.game)
        e.update(md)
        suffix = "_max" if a.style == "max" else ("_pro" if e["kind"] == "short" else "_final")
        final = OUT / e["file"].replace("_raw", suffix)
        if not final.exists():
            print(f"editing {e['file']}  ({e['hook']})  style={a.style}")
            if a.style == "max":
                from . import max as maxstyle
                maxstyle.render(e, vid, tag=a.tag or meta.GAMES[a.game]["tag_chip"])
            elif e["kind"] == "short":
                style_pro.render(e, vid)
            else:
                edit.edit_clip(e, vid)
        thumb_name = None
        if e["kind"] == "video":
            thumb_name = final.stem + "_thumb.jpg"
            thumb.make(RAW / e["file"], e["hook"], AUX / "thumbs" / thumb_name)
        e["final"], e["thumb"] = final.name, thumb_name
        if not a.no_queue:
            uploader.enqueue({"file": final.name, "kind": e["kind"], "title": e["title"],
                              "description": e["description"], "tags": e["tags"], "thumb": thumb_name})
        mp.write_text(json.dumps(entries, indent=1), encoding="utf-8")
    print(f"\nDone. {len(entries)} clips ready in {OUT}. Queue: python -m clipx.uploader status")


if __name__ == "__main__":
    main()
