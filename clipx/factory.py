"""Mass production: themes -> viral sources (YouTube API) -> download -> best moments -> pro specs -> render + QA.

  python -m clipx.factory plan              # search every theme, write factory\\sources.json
  python -m clipx.factory feed              # download each source, find peaks, write specs (runs for hours)
  python -m clipx.factory work              # render specs one by one with QA (start 1-2 of these in parallel)
  python -m clipx.factory status
Everything is resumable. Nothing is queued or uploaded here. Finished clips land in output\\, rejected ones in
other\\rejected with the reason in other\\qa. Upload metadata per clip is saved in factory\\meta\\<slug>.json.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from .config import ROOT, WORK, OUT, AUX

F = ROOT / "factory"
SPECS, META, LOCK, DONE = F / "specs", F / "meta", F / "lock", F / "done"
REJ = AUX / "rejected"
for _d in (F, SPECS, META, LOCK, DONE, REJ):
    _d.mkdir(parents=True, exist_ok=True)

BAD_TITLE = ("strip", "nude", "naked", "sex", "18+", "nsfw", "trailer", "reaction", "reacts", "news", "leak", "review",
             "podcast", "theory", "before you buy", "explained", "everything we know", "live", "stream", "#shorts", "roblox",
             "minecraft", "fortnite", "mod ", "mods", "real life", "irl", "movie")

# theme: queries, on-screen titles (2 lines), upload title patterns, caption beats, extra tags
THEMES = {
    "fight": (["GTA 6 fight gameplay", "GTA 6 NPC fight brawl"],
              [["STREET FIGHT", "GETS OUT OF HAND"], ["ONE PUNCH", "STARTED IT ALL"], ["NPCS", "FIGHT BACK"]],
              ["GTA 6 Street Fight Gets Out of Hand", "GTA 6 NPCs Fight Back", "GTA 6 Brawl - Nobody Backs Down"],
              ["IT STARTED SMALL", "THEN IT SPREAD", "NOBODY BACKS DOWN"], ["GTA 6 fight", "GTA 6 NPC"]),
    "chase": (["GTA 6 police chase gameplay", "GTA 6 5 star wanted level escape"],
              [["POLICE CHASE", "NO WAY OUT"], ["5 STARS", "FULL SPEED"], ["COPS", "EVERYWHERE"]],
              ["GTA 6 Police Chase - No Way Out", "GTA 6 Wanted Level Escape", "GTA 6 Cops Everywhere"],
              ["THE CHASE IS ON", "COPS ON ALL SIDES", "CAN HE ESCAPE"], ["GTA 6 police chase", "GTA 6 wanted level"]),
    "stunt": (["GTA 6 stunts", "GTA 6 bike stunts jumps"],
              [["INSANE", "STUNT"], ["HE ACTUALLY", "LANDED IT"], ["BIGGEST JUMP", "IN VICE CITY"]],
              ["GTA 6 Insane Stunt", "GTA 6 Biggest Jump in Vice City", "GTA 6 Stunt - Did He Land It?"],
              ["FULL SEND", "NO BRAKES", "DID HE LAND IT"], ["GTA 6 stunts", "GTA 6 jump"]),
    "crash": (["GTA 6 car crashes", "GTA 6 crash physics"],
              [["BRUTAL", "CRASH"], ["CRASH PHYSICS", "LOOK REAL"], ["TOTAL", "WRECK"]],
              ["GTA 6 Brutal Crash", "GTA 6 Crash Physics Look Real", "GTA 6 Total Wreck"],
              ["TOO FAST", "NO TIME TO BRAKE", "LOOK AT THE DAMAGE"], ["GTA 6 crash", "GTA 6 physics"]),
    "secret": (["GTA 6 secret locations", "GTA 6 hidden places easter eggs"],
               [["HIDDEN PLACE", "MOST PLAYERS MISS"], ["SECRET SPOT", "IN VICE CITY"], ["EASTER EGG", "FOUND"]],
               ["GTA 6 Hidden Place Most Players Miss", "GTA 6 Secret Spot in Vice City", "GTA 6 Easter Egg Found"],
               ["MOST PLAYERS MISS THIS", "LOOK CLOSER", "DID YOU KNOW THIS"], ["GTA 6 secrets", "GTA 6 easter eggs", "GTA 6 hidden"]),
    "glitch": (["GTA 6 glitches", "GTA 6 funny moments fails"],
               [["GTA 6", "GLITCH"], ["THIS WASN'T", "SUPPOSED TO HAPPEN"], ["FUNNY", "FAIL"]],
               ["GTA 6 Glitch - This Wasn't Supposed To Happen", "GTA 6 Funny Fail", "GTA 6 Broke Itself"],
               ["THIS IS NOT NORMAL", "WAIT WHAT", "THE GAME BROKE"], ["GTA 6 glitch", "GTA 6 funny moments", "GTA 6 fails"]),
    "tips": (["GTA 6 money glitch", "GTA 6 tips and tricks"],
             [["TRICK", "YOU NEED TO KNOW"], ["EASY", "MONEY"], ["PRO TIP", "GTA 6"]],
             ["GTA 6 Trick You Need To Know", "GTA 6 Easy Money Method", "GTA 6 Pro Tip"],
             ["MOST PLAYERS SKIP THIS", "HERE IS THE TRICK", "TRY THIS NEXT"], ["GTA 6 tips", "GTA 6 money", "GTA 6 tricks"]),
    "beach": (["GTA 6 beach gameplay", "GTA 6 Vice Beach NPC"],
              [["VICE BEACH", "LOOKS UNREAL"], ["BEACH DAY", "IN GTA 6"], ["OCEAN BEACH", "VIBES"]],
              ["GTA 6 Vice Beach Looks Unreal", "GTA 6 Beach Day", "GTA 6 Ocean Beach Vibes"],
              ["LOOK AT THE CROWD", "EVERY NPC IS DIFFERENT", "FEELS LIKE REAL LIFE"], ["GTA 6 beach", "Ocean Beach"]),
    "night": (["GTA 6 nightclub gameplay", "GTA 6 Vice City night life"],
              [["VICE CITY", "AFTER DARK"], ["NIGHTCLUB", "IN GTA 6"], ["NEON", "NIGHTS"]],
              ["GTA 6 Vice City After Dark", "GTA 6 Nightclub Scene", "GTA 6 Neon Nights"],
              ["THE CITY WAKES UP", "NEON EVERYWHERE", "THE NIGHT IS YOUNG"], ["GTA 6 nightclub", "GTA 6 nightlife"]),
    "story": (["GTA 6 Lucia Jason scene", "GTA 6 cutscene"],
              [["JASON", "& LUCIA"], ["THE SCENE", "EVERYONE TALKS ABOUT"], ["LUCIA", "MOMENT"]],
              ["GTA 6 Jason & Lucia Scene", "GTA 6 The Scene Everyone Talks About", "GTA 6 Lucia Moment"],
              ["THE TENSION IS REAL", "SHE MEANS IT", "WHAT HAPPENS NEXT"], ["GTA 6 Lucia", "GTA 6 Jason", "GTA 6 cutscene"]),
    "mission": (["GTA 6 mission no commentary", "GTA 6 walkthrough no commentary"],
                [["MISSION", "GOES WRONG"], ["THE PLAN", "FALLS APART"], ["MISSION", "HIGHLIGHT"]],
                ["GTA 6 Mission Goes Wrong", "GTA 6 The Plan Falls Apart", "GTA 6 Mission Highlight"],
                ["THE PLAN WAS SIMPLE", "THEN IT WENT WRONG", "NO TURNING BACK"], ["GTA 6 mission", "GTA 6 walkthrough"]),
    "heist": (["GTA 6 heist robbery gameplay", "GTA 6 store robbery"],
              [["ROBBERY", "IN PROGRESS"], ["THE HEIST", "BEGINS"], ["GRAB IT", "AND RUN"]],
              ["GTA 6 Robbery In Progress", "GTA 6 The Heist Begins", "GTA 6 Grab It And Run"],
              ["IN AND OUT", "ALARM IS RINGING", "TIME TO RUN"], ["GTA 6 heist", "GTA 6 robbery"]),
    "ride": (["GTA 6 supercars gameplay", "GTA 6 plane helicopter boat gameplay"],
             [["FASTEST RIDE", "IN VICE CITY"], ["TOP SPEED", "TEST"], ["TAKING OFF", "IN GTA 6"]],
             ["GTA 6 Fastest Ride in Vice City", "GTA 6 Top Speed Test", "GTA 6 Taking Off"],
             ["LISTEN TO THAT ENGINE", "FULL THROTTLE", "HOW FAST CAN IT GO"], ["GTA 6 cars", "GTA 6 vehicles"]),
    "world": (["GTA 6 details", "GTA 6 animals wildlife"],
              [["TINY DETAIL", "HUGE DIFFERENCE"], ["THE DETAILS", "ARE INSANE"], ["WILDLIFE", "IN LEONIDA"]],
              ["GTA 6 Tiny Detail, Huge Difference", "GTA 6 The Details Are Insane", "GTA 6 Wildlife in Leonida"],
              ["LOOK CLOSELY", "ROCKSTAR THOUGHT OF THIS", "DID YOU NOTICE"], ["GTA 6 details", "GTA 6 graphics"]),
    "shoot": (["GTA 6 shootout gameplay", "GTA 6 gunfight"],
              [["SHOOTOUT", "NO COVER"], ["GUNFIGHT", "IN VICE CITY"], ["LAST", "STAND"]],
              ["GTA 6 Shootout - No Cover", "GTA 6 Gunfight in Vice City", "GTA 6 Last Stand"],
              ["SHOTS FIRED", "TAKING COVER", "ONE LEFT"], ["GTA 6 shootout", "GTA 6 gunfight"]),
    "roam": (["GTA 6 free roam 4K", "GTA 6 exploring Vice City"],
             [["VICE CITY", "FREE ROAM"], ["EXPLORING", "LEONIDA"], ["THIS CITY", "FEELS ALIVE"]],
             ["GTA 6 Vice City Free Roam", "GTA 6 Exploring Leonida", "GTA 6 This City Feels Alive"],
             ["JUST LOOK AT IT", "EVERY STREET IS ALIVE", "WHERE WOULD YOU GO"], ["GTA 6 free roam", "GTA 6 4K"]),
}
DIS = ("Not affiliated with or endorsed by Rockstar Games or Take-Two Interactive. "
       "Grand Theft Auto is a trademark of Take-Two Interactive Software, Inc.")
BASE_TAGS = ["GTA 6", "GTA VI", "GTA 6 gameplay", "Grand Theft Auto VI", "Vice City", "Rockstar Games", "gta6"]


def log(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(F / "factory.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ------------------------------------------------------------------ plan
# Raw-gameplay only. Explainer / news / commentary videos are full of infographics and talking, which made junk clips.
RAW_QUERIES = ["GTA 6 gameplay no commentary", "GTA 6 walkthrough no commentary 4K", "GTA 6 mission walkthrough PS5 4K",
               "GTA 6 free roam gameplay 4K", "GTA 6 police chase gameplay no commentary", "GTA 6 shootout gameplay",
               "GTA 6 heist mission gameplay", "GTA 6 fight gameplay no commentary", "GTA 6 stunts gameplay",
               "GTA 6 car crashes compilation", "GTA 6 beach gameplay 4K", "GTA 6 nightclub gameplay",
               "GTA 6 scene 4K", "GTA 6 funny moments fails compilation", "GTA 6 driving gameplay 4K",
               "GTA 6 plane helicopter gameplay", "GTA 6 secret location gameplay", "GTA 6 rampage gameplay"]
MUST_HAVE = ("gameplay", "no commentary", "walkthrough", "mission", "scene", "free roam", "shootout", "4k", "compilation",
             "rampage", "heist", "robbery", "chase", "cutscene", "funny moments", "fails")
EXPLAINER = ("why ", "how ", "what ", "inside ", "explained", "everything", "things", "facts", "details", "secrets", "tips",
             "guide", "ranking", "ranked", "top ", "best ", "worst", "review", "vs ", "comparison", "news", "leak", "trailer",
             "react", "reaccion", "theory", "rumor", "confirmed", "release", "edition", "buy", "datamined", "impossible",
             "blew", "too real", "not ready", "reveal", "changed", "fix", "flaws", "wrong", "problem", "i tried", "i did",
             "i robbed", "i shot", "i downloaded", "i stole", "i triggered", "can you", "will be", "should", "gta 5", "gta v",
             "gta online", "vr", "concept", "fan made", "fanmade", "unreal engine", "mod", "podcast", "live", "stream",
             "strip", "nude", "naked", "sex", "18+", "nsfw", "motel", "bedroom", "shower", "seduce", "romance scene",
             "roblox", "minecraft", "real life", "irl", "#shorts")
THEME_KEYS = [("heist", ("heist", "robbery", "bank", "robbing")), ("shoot", ("shootout", "gunfight", "shooting", "gang")),
              ("chase", ("chase", "wanted", "police", "stars", "cops", "evading", "rampage")), ("fight", ("fight", "brawl", "punch")),
              ("stunt", ("stunt", "jump", "bike")), ("crash", ("crash", "damage")), ("glitch", ("funny", "fail", "glitch")),
              ("beach", ("beach",)), ("night", ("night", "club")), ("ride", ("driving", "car", "plane", "helicopter", "boat", "jet", "drive")),
              ("secret", ("secret", "hidden", "easter")), ("story", ("scene", "cutscene", "lucia", "jason", "prologue")),
              ("mission", ("mission", "walkthrough", "chapter")), ("roam", ("free roam", "explor", "open world"))]


def theme_of(title):
    t = title.lower()
    for th, keys in THEME_KEYS:
        if any(k in t for k in keys):
            return th
    return "roam"


def plan(max_sources=110):
    from . import discover
    used = {p.stem for p in WORK.glob("*.mp4")}
    out = []
    for q in RAW_QUERIES:
        try:
            res = discover.search(q, n=40, days=45, min_min=6, max_min=45)
        except Exception as e:
            log("search failed", q, str(e)[:100])
            continue
        kept = 0
        for r in res:
            t = r["title"].lower()
            if r["id"] in used or r["rights"] == "blocked":
                continue
            if not ("gta 6" in t or "gta vi" in t or "gta6" in t or "grand theft auto 6" in t or "grand theft auto vi" in t):
                continue
            if not any(m in t for m in MUST_HAVE) or any(b in t for b in EXPLAINER):
                continue
            used.add(r["id"])
            out.append({**r, "theme": theme_of(r["title"])})
            kept += 1
        log(q, "->", kept)
    out = sorted(out, key=lambda r: -r["views"])[:max_sources]
    by = {}
    for x in out:
        by.setdefault(x["theme"], []).append(x)
    from itertools import zip_longest
    mix = [x for row in zip_longest(*by.values()) for x in row if x]      # interleave themes
    (F / "sources.json").write_text(json.dumps(mix, indent=1, ensure_ascii=False), encoding="utf-8")
    log("plan done:", len(mix), "sources", {k: len(v) for k, v in by.items()})


def reset():
    """Park the current run's state (nothing is deleted) so a new plan starts clean."""
    old = F / ("old_" + time.strftime("%m%d_%H%M%S"))
    old.mkdir()
    for name in ("specs", "meta", "done", "lock", "fed.json", "FEED_DONE", "sources.json"):
        p = F / name
        if p.exists():
            shutil.move(str(p), str(old / name))
    for d in (SPECS, META, LOCK, DONE):
        d.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("pro_f_*.mp4"):
        shutil.move(str(f), str(REJ / f.name))
    log("reset: old state moved to", old.name)


# ------------------------------------------------------------------ feed
def _download(vid):
    import yt_dlp
    dst = WORK / f"{vid}.mp4"
    if dst.exists() and (WORK / f"{vid}.meta.json").exists():
        return True
    opts = {"format": "bv*[height<=1080]+ba/b[height<=1080]", "merge_output_format": "mp4", "outtmpl": str(WORK / "%(id)s.%(ext)s"),
            "quiet": True, "noprogress": True, "no_warnings": True, "retries": 3}
    if not shutil.which("deno") and shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
    ck = ROOT / "secrets" / "youtube_cookies.txt"          # optional: exported browser cookies (never printed)
    if ck.exists():
        opts["cookiefile"] = str(ck)
        # with a login attached the default client hides the formats; this client returns them (tested 2026-11-20)
        opts["extractor_args"] = {"youtube": {"player_client": ["tv_embedded"]}}
    with yt_dlp.YoutubeDL(opts) as y:
        i = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
    (WORK / f"{vid}.meta.json").write_text(json.dumps({
        "id": vid, "title": i.get("title"), "channel": i.get("channel"), "url": f"https://www.youtube.com/watch?v={vid}",
        "duration": i.get("duration"), "license": i.get("license")}, indent=1), encoding="utf-8")
    return dst.exists()


def peaks(vid, n=14, win=6.0, sep=45.0, head=25.0, tail=40.0):
    """Loud + fast-moving moments (audio energy + frame motion), at least `sep` seconds apart."""
    p = str(WORK / f"{vid}.mp4")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    h = 4000
    m = len(a) // h
    e = np.sqrt((a[:m * h].reshape(m, h) ** 2).mean(1))
    fr = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", "fps=2,scale=96:54", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    f = np.frombuffer(fr, np.uint8).reshape(-1, 54, 96).astype(np.float32)
    if len(f) < 60 or len(e) < 60:
        return [], 0.0
    mo = np.abs(np.diff(f, axis=0)).mean((1, 2))
    mo = np.append(mo, mo[-1])
    L = min(len(e), len(mo))
    e, mo = e[:L], mo[:L]
    z = lambda x: (x - x.mean()) / (x.std() + 1e-6)
    s = z(e) + z(np.clip(mo, 0, np.percentile(mo, 98)))
    k = int(win * 2)
    sc = np.convolve(s, np.ones(k) / k, mode="valid")
    dur = L / 2
    out = []
    for i in np.argsort(-sc):
        t = i / 2 + win / 2
        if t < head or t > dur - tail:
            continue
        if all(abs(t - u) >= sep for u in out):
            out.append(float(round(t, 1)))
        if len(out) >= n:
            break
    return out, dur


def _write(slug, spec, meta):
    (SPECS / f"{slug}.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    (META / f"{slug}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")


VIDEO_CAP = 20      # total long videos wanted; every other strong moment becomes a Short


def _n_videos():
    return len([p for p in SPECS.glob("*.json") if "_v" in p.stem[-4:]])


def reshape():
    """Keep VIDEO_CAP long videos (finished ones + a spread of themes); turn every other planned video into Shorts."""
    state_f = F / "fed.json"
    state = json.loads(state_f.read_text(encoding="utf-8"))
    vs = sorted(p for p in SPECS.glob("*.json") if "_v" in p.stem[-4:])
    keep = [p for p in vs if (DONE / p.stem).exists() and (DONE / p.stem).read_text().strip() == "ok"]
    rest = [p for p in vs if p not in keep and not (DONE / p.stem).exists()]
    by = {}
    for p in rest:
        by.setdefault(p.stem.split("_")[1], []).append(p)
    have = {}
    for p in keep:
        have[p.stem.split("_")[1]] = have.get(p.stem.split("_")[1], 0) + 1
    while len(keep) < VIDEO_CAP and any(by.values()):
        th = min((t for t in by if by[t]), key=lambda t: (have.get(t, 0), t))      # thinnest theme first
        keep.append(by[th].pop(0))
        have[th] = have.get(th, 0) + 1
    made = 0
    for p in rest:
        if p in keep:
            continue
        spec, meta = json.loads(p.read_text(encoding="utf-8")), json.loads((META / p.name).read_text(encoding="utf-8"))
        vid = meta["source"]
        mf = WORK / f"{vid}.meta.json"
        dur = float(json.loads(mf.read_text(encoding="utf-8")).get("duration") or 1e9) if mf.exists() else 1e9
        for pc in spec["pieces"]:
            t = round((pc["s"] + pc["e"]) / 2, 1)
            if t - 22 < 2 or t + 16 > dur - 2:
                continue
            _short(vid, meta["theme"], t, dur, state["counters"])
            made += 1
        p.unlink()
        (META / p.name).unlink()
    state_f.write_text(json.dumps(state), encoding="utf-8")
    print(f"videos kept {len(keep)}: {sorted(q.stem for q in keep)}\nnew shorts {made}")


def _short(vid, theme, t, dur, counters):
    _q, screens, titles, beats, tags = THEMES[theme]
    for _once in (0,):
        i = counters[theme + "_s"] = counters.get(theme + "_s", 0) + 1
        slug = f"f_{theme}_s{i:02d}"
        a, b = max(2.0, t - 22), min(dur - 2, t + 16)
        scr = screens[(i - 1) % len(screens)]
        spec = {"slug": slug, "kind": "short", "src": f"work/{vid}.mp4", "tag": "GTA 6", "layout": "tall", "title": scr, "vcrop": 0.8, "vy": 0.1,
                "pieces": [{"s": t, "e": min(t + 2, dur - 1), "speed": 0.5, "cx": 0.5, "zoom": "in"},
                           {"s": a, "e": b, "cx": 0.5, "zoom": "out", "tr": "whip"}],
                "caps": [{"p": 0, "t": 0.3, "d": 2.2, "text": ["WAIT FOR IT", "WATCH THIS", "LOOK AT THIS"][(i - 1) % 3]},
                         {"p": 1, "t": 0.6, "d": 2.6, "text": beats[0]}, {"p": 1, "t": 13.0, "d": 2.6, "text": beats[1]},
                         {"p": 1, "t": 27.0, "d": 2.6, "text": beats[2]}],
                "flash": [{"p": 1, "t": 0.0}], "sfx": [{"p": 0, "t": 0.05, "k": "impact"}]}
        ttl = f"{titles[(i - 1) % len(titles)]} #{i} #Shorts"
        _write(slug, spec, {"kind": "short", "title": ttl, "tags": (BASE_TAGS + tags)[:15], "thumb": None, "source": vid, "theme": theme,
                            "description": f"{titles[(i - 1) % len(titles)]}. What would you have done? Tell me in the comments, and follow for more GTA 6 clips.\n\n{DIS}\n\n#GTA6 #GTAVI #ViceCity #Shorts"})


def make_specs(src, counters):
    vid, theme = src["id"], src["theme"]
    _q, screens, titles, beats, tags = THEMES[theme]
    pk, dur = peaks(vid)
    if len(pk) < 3:
        log("  too few moments in", vid)
        return 0
    want_video = _n_videos() < VIDEO_CAP and len(pk) >= 7
    n_short = len(pk) - 5 if want_video else len(pk)
    vids = [sorted(pk[n_short:])] if want_video else []
    made = 0
    for j in range(n_short):
        _short(vid, theme, pk[j], dur, counters)
        made += 1
    for wins in vids:
        i = counters[theme + "_v"] = counters.get(theme + "_v", 0) + 1
        slug = f"f_{theme}_v{i:02d}"
        scr = screens[(i - 1) % len(screens)]
        pcs = [{"s": max(1.0, t - 13), "e": min(dur - 1, t + 13), "cx": 0.5, "zoom": "in" if k % 2 == 0 else "out", "tr": "fade"} for k, t in enumerate(wins)]
        caps = [{"p": k, "t": 0.5, "d": 3, "text": (beats + ["IT KEEPS GOING", "ONE MORE"])[k % 5]} for k in range(len(pcs))]
        spec = {"slug": slug, "kind": "video", "src": f"work/{vid}.mp4", "tag": "GTA 6", "vcrop": 0.95, "title": scr, "pieces": pcs, "caps": caps,
                "flash": [], "sfx": []}
        ttl = f"{titles[(i - 1) % len(titles)]} - Best Moments #{i}"
        _write(slug, spec, {"kind": "video", "title": ttl, "tags": (BASE_TAGS + tags)[:15], "thumb": f"pro_{slug}_thumb.jpg", "thumb_at": wins[0],
                            "thumb_hook": " ".join(scr), "source": vid, "theme": theme,
                            "description": f"{titles[(i - 1) % len(titles)]}: the best moments in one video. Which part was your favourite? Tell me in the comments, and subscribe for more GTA 6 clips.\n\n{DIS}\n\n#GTA6 #GTAVI #ViceCity"})
        made += 1
    return made


def feed():
    srcs = json.loads((F / "sources.json").read_text(encoding="utf-8"))
    state_f = F / "fed.json"
    state = json.loads(state_f.read_text(encoding="utf-8")) if state_f.exists() else {"done": [], "counters": {}}
    srcs.sort(key=lambda s: not (WORK / f"{s['id']}.mp4").exists())   # files already on disk first (stable)
    for s in srcs:
        if s["id"] in state["done"]:
            continue
        try:
            log("feed", s["theme"], s["id"], s["title"][:50].encode("ascii", "replace").decode())
            if _download(s["id"]):
                n = make_specs(s, state["counters"])
                log("  specs written:", n)
        except Exception as e:
            log("  FAILED", s["id"], str(e)[:160].encode("ascii", "replace").decode())
            if "not a bot" in str(e):                 # YouTube is rate-limiting this PC: stop, retry later
                log("feed paused: YouTube bot-check. Run `python -m clipx.factory feed` again later.")
                return
            state.setdefault("failed", []).append(s["id"])
        state["done"].append(s["id"])
        state_f.write_text(json.dumps(state), encoding="utf-8")
        time.sleep(150)                               # be gentle: avoids the bot-check
    (F / "FEED_DONE").write_text("done", encoding="utf-8")
    log("feed finished")


# ------------------------------------------------------------------ work
def work():
    from . import pro, qa, thumb
    idle = 0
    while True:
        vfirst = os.environ.get("CLIPX_PREFER") == "video"      # one worker can be told to do the long videos first
        todo = [p for p in sorted(SPECS.glob("*.json"), key=lambda q: (("_v" in q.stem[-4:]) != vfirst, q.stem))   # default: Shorts first
                if not (DONE / p.stem).exists() and not (LOCK / p.stem).exists()]
        if not todo:
            if (F / "FEED_DONE").exists():
                break
            idle += 1
            time.sleep(60)
            continue
        sp = todo[0]
        try:
            open(LOCK / sp.stem, "x").close()
        except FileExistsError:
            continue
        slug = sp.stem
        t0 = time.time()
        try:
            spec = json.loads(sp.read_text(encoding="utf-8"))
            dst, dur = pro.render(spec)
            r = qa.check(dst)
            if r["ok"]:
                m = json.loads((META / f"{slug}.json").read_text(encoding="utf-8"))
                if m.get("thumb"):
                    try:
                        thumb.make(ROOT / spec["src"], m["thumb_hook"], AUX / "thumbs" / m["thumb"], at=m["thumb_at"], crop=(0.03, 0.03, 0.97, 0.86))
                    except Exception as e:
                        log("  thumb failed", slug, str(e)[:80])
                log(f"OK   {slug} {dur:.0f}s in {(time.time() - t0) / 60:.1f} min")
                (DONE / slug).write_text("ok", encoding="utf-8")
            else:
                shutil.move(str(dst), str(REJ / dst.name))
                (AUX / "qa").mkdir(exist_ok=True)
                (AUX / "qa" / f"{dst.stem}.bad").write_text("; ".join(r["reasons"]), encoding="utf-8")
                log(f"VETO {slug}: " + "; ".join(r["reasons"]))
                (DONE / slug).write_text("veto", encoding="utf-8")
        except Exception as e:
            log(f"FAIL {slug}: {str(e)[:200]}")
            (DONE / slug).write_text("fail", encoding="utf-8")
            for junk in OUT.glob(f"pro_{slug}.mp4"):
                junk.unlink(missing_ok=True)
        finally:
            (LOCK / slug).unlink(missing_ok=True)
    log("worker finished")


def unlock():
    """After a crash / reboot: clear stale locks and half-written outputs so the work is picked up again."""
    n = 0
    for l in LOCK.iterdir():
        for junk in OUT.glob(f"pro_{l.name}.mp4"):
            junk.unlink(missing_ok=True)
        l.unlink(missing_ok=True)
        n += 1
    log("unlock: cleared", n, "stale locks")


def status():
    res = {"ok": 0, "veto": 0, "fail": 0}
    kinds = {"short": 0, "video": 0}
    for d in DONE.iterdir():
        v = d.read_text(encoding="utf-8")
        res[v] = res.get(v, 0) + 1
        if v == "ok":
            kinds["video" if "_v" in d.name[-4:] else "short"] += 1
    specs = len(list(SPECS.glob("*.json")))
    srcs = len(json.loads((F / "sources.json").read_text(encoding="utf-8"))) if (F / "sources.json").exists() else 0
    fed = len(json.loads((F / "fed.json").read_text(encoding="utf-8"))["done"]) if (F / "fed.json").exists() else 0
    print(f"sources {fed}/{srcs} fetched | specs {specs} | rendered ok {res['ok']} (shorts {kinds['short']}, videos {kinds['video']}) | "
          f"vetoed {res['veto']} | failed {res['fail']} | feed {'finished' if (F / 'FEED_DONE').exists() else 'running'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"plan": plan, "feed": feed, "work": work, "status": status, "reset": reset, "unlock": unlock, "reshape": reshape}[cmd]()
