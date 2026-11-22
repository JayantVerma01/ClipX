"""Audience signals for picking moments - the idea GTA-Auto-Clipper is best at (live-chat reactions), adapted to VODs.

Their tool reads the LIVE chat while recording a stream. We mostly work from finished videos, so we use the two audience
signals YouTube keeps after the fact:
  * chat replay   (yt-dlp can download it for videos that were live streams): bursts of different people reacting
  * 'most replayed' heatmap (yt-dlp exposes it when YouTube shows the graph)
Both become a per-second score (0..4) that clipx.moments adds to the audio / speech score.
Spam from one chatter is de-weighted (same rule as theirs): only DISTINCT lines per chatter count, many different
chatters count more, and reaction words / emoji count most.
"""
import json
import re
import shutil
from .config import WORK
import numpy as np

REACTION = re.compile(
    r"\b(?:lol|lmao|rofl|wtf|omg|no way|clip it|clip that|insane|crazy|rip|bruh|that was close|what just happened|"
    r"holy (?:shit|crap)|let'?s go+|pog|poggers|kekw|omegalul|lul|gg)\b|😂|🤣|💀|😱|😮|🔥|😭",
    re.IGNORECASE)


def is_reaction(text):
    return bool(REACTION.search(str(text or "")))


def score_chat(messages, duration, win=10.0, step=5.0):
    """Pure logic (unit-tested). messages: [{'t': seconds, 'user': str, 'text': str}]. Returns a per-second array 0..4."""
    n = int(np.ceil(duration))
    out = np.zeros(max(n, 1))
    if not messages or n <= 0:
        return out
    starts = np.arange(0, max(duration - win, 0) + 1e-6, step)
    rows = []
    for s in starts:
        sel = [m for m in messages if s <= float(m["t"]) < s + win]
        by_user = {}
        for m in sel:
            u = str(m.get("user") or "?").casefold()
            by_user.setdefault(u, set()).add(re.sub(r"\s+", " ", str(m.get("text") or "")).strip().casefold())
        chatters = len(by_user)
        reacting = sum(1 for texts in by_user.values() if any(is_reaction(t) for t in texts))
        distinct = sum(len(t) for t in by_user.values())
        rows.append((s, min(distinct, chatters * 3), chatters, reacting))
    act = np.array([r[1] for r in rows], dtype=float)
    med = float(np.median(act))
    mad = max(1.0, float(np.median(np.abs(act - med))))
    for (s, a, chatters, reacting) in rows:
        burst = max(0.0, (a - med) / mad)
        signal = min(2.5, burst * 0.55) + min(chatters, 16) / 16 * 0.75 + min(reacting, 5) / 5 * 1.25
        signal = min(4.0, signal)
        i0, i1 = int(s), min(n, int(s + win))
        out[i0:i1] = np.maximum(out[i0:i1], signal)
    return out


def score_heatmap(heatmap, duration):
    """Pure logic. heatmap = [{'start_time','end_time','value'}] (value 0..1). Returns a per-second array 0..4 where
    only clearly above-average replay spots count."""
    n = int(np.ceil(duration))
    out = np.zeros(max(n, 1))
    if not heatmap:
        return out
    vals = np.array([float(h["value"]) for h in heatmap])
    base = float(np.median(vals))
    for h in heatmap:
        lift = (float(h["value"]) - base) / max(1e-6, (1.0 - base))
        if lift > 0:
            i0, i1 = int(h["start_time"]), min(n, int(np.ceil(h["end_time"])))
            out[i0:i1] = np.maximum(out[i0:i1], 4.0 * lift)
    return out


def parse_chat_replay(path):
    """Read a yt-dlp live_chat.json file (one JSON object per line) into [{'t','user','text'}]."""
    msgs = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            act = obj.get("replayChatItemAction") or {}
            off = act.get("videoOffsetTimeMsec", obj.get("videoOffsetTimeMsec"))
            try:
                t = int(off) / 1000.0
            except (TypeError, ValueError):
                continue
            for a in act.get("actions", []):
                item = (a.get("addChatItemAction") or {}).get("item") or {}
                for key in ("liveChatTextMessageRenderer", "liveChatPaidMessageRenderer"):
                    r = item.get(key)
                    if not r:
                        continue
                    runs = (r.get("message") or {}).get("runs", [])
                    text = "".join(x.get("text") or (x.get("emoji") or {}).get("emojiId", "") for x in runs)
                    user = r.get("authorExternalChannelId") or (r.get("authorName") or {}).get("simpleText")
                    msgs.append({"t": t, "user": user, "text": text})
    return msgs


def fetch(vid, duration, force=False):
    """Download (once, cached) chat replay + heatmap for a YouTube video and return (array or None, [source names])."""
    cache = WORK / f"{vid}.signals.json"
    if cache.exists() and not force:
        d = json.loads(cache.read_text(encoding="utf-8"))
    else:
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True, "skip_download": True, "writesubtitles": True,
                "subtitleslangs": ["live_chat"], "outtmpl": str(WORK / "%(id)s.%(ext)s")}
        if not shutil.which("deno") and shutil.which("node"):
            opts["js_runtimes"] = {"node": {}}
        d = {"heatmap": None, "chat": 0}
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
            d["heatmap"] = info.get("heatmap")
        except Exception as e:            # chat replay missing / blocked is normal for non-stream videos
            d["error"] = str(e)[:160]
        chat_file = WORK / f"{vid}.live_chat.json"
        if chat_file.exists():
            msgs = parse_chat_replay(chat_file)
            d["chat"] = len(msgs)
            d["messages"] = msgs
        cache.write_text(json.dumps(d), encoding="utf-8")
    total = np.zeros(max(int(np.ceil(duration)), 1))
    used = []
    if d.get("messages"):
        total = np.maximum(total, score_chat(d["messages"], duration))
        used.append(f"chat replay ({d['chat']} messages)")
    if d.get("heatmap"):
        total = np.maximum(total, score_heatmap(d["heatmap"], duration))
        used.append("most-replayed heatmap")
    return (total if used else None), used
