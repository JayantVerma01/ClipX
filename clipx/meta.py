"""Titles, hooks, descriptions, tags. Template-based: zero LLM tokens. Game-aware (gta6 / gta5)."""
import re
from collections import Counter

GAMES = {
    "gta6": {
        "name": "GTA 6", "full": "Grand Theft Auto VI", "tag_chip": "GTA 6",
        "hashtags": "#GTA6 #GTAVI #RockstarGames",
        # Only publicly known characters/places (Whisper mishears names, so free-form detection gave junk).
        "known": {"lucia": "Lucia", "jason": "Jason", "cal": "Cal", "boobie": "Boobie", "booby": "Boobie",
                  "boobies": "Boobie", "andres": "Andres", "raul": "Raul", "brian": "Brian", "drequan": "Dre'Quan",
                  "roxy": "Roxy", "leonida": "Leonida", "vice city": "Vice City"},
        "base_tags": ["GTA 6", "GTA VI", "GTA 6 gameplay", "Grand Theft Auto VI", "Vice City", "Rockstar Games",
                      "Lucia", "Jason", "GTA 6 news", "gta6"],
    },
    "gta5": {
        "name": "GTA 5", "full": "Grand Theft Auto V", "tag_chip": "GTA 5",
        "hashtags": "#GTA5 #GTAV #RockstarGames",
        "known": {"franklin": "Franklin", "lamar": "Lamar", "michael": "Michael", "trevor": "Trevor", "chop": "Chop",
                  "stretch": "Stretch", "devin": "Devin", "simeon": "Simeon", "lester": "Lester", "amanda": "Amanda",
                  "jimmy": "Jimmy", "tracey": "Tracey", "los santos": "Los Santos", "tanisha": "Tanisha"},
        "base_tags": ["GTA 5", "GTA V", "GTA 5 gameplay", "Grand Theft Auto V", "Los Santos", "Rockstar Games",
                      "Franklin", "Michael", "Trevor", "GTA 5 walkthrough", "gta5"],
    },
}
TITLES_SHORT = ["{h} | {g} Scene", "{g}: {h} Moment", "{h} in {g} (Watch This)", "{g} - {h} Breakdown"]
TITLES_VIDEO = ["{g}: {h} - Full Scene", "{h} | {g} Best Moments", "{g} - Everything In The {h} Scene"]
DISCLAIMER = ("Not affiliated with or endorsed by Rockstar Games or Take-Two Interactive. "
              "Grand Theft Auto is a trademark of Take-Two Interactive Software, Inc.")


def entities(text, known, n=2):
    low = text.lower()
    c = Counter()
    for k, disp in known.items():
        hits = len(re.findall(r"\b" + re.escape(k) + r"\b", low))
        if hits:
            c[disp] += hits
    return [w for w, _ in c.most_common(n)]


def make(entry, idx, source=None, game="gta6"):
    G = GAMES[game]
    ents = entities(entry.get("text", ""), G["known"])
    fallback = [f"{G['name']} SCENE", f"{G['name']} MOMENT", f"{G['name']} CLIP"][idx % 3]
    hook = " & ".join(e.upper() for e in ents) if ents else fallback
    kind = entry["kind"]
    tpl = (TITLES_SHORT if kind == "short" else TITLES_VIDEO)[idx % (4 if kind == "short" else 3)]
    h = hook.title().replace("Gta", "GTA")
    title = (tpl.format(h=h, g=G["name"]) if ents else f"{h} #{idx + 1} | {G['full'].replace('Grand Theft Auto', 'GTA')}")[:95]
    lines = [f"{h} - {G['name']}", ""]
    if source:
        lines += [f"Source: {source}", ""]
    lines += [DISCLAIMER, "", G["hashtags"] + (" #Shorts" if kind == "short" else "")]
    return {"hook": hook, "title": title + (" #Shorts" if kind == "short" and "#Shorts" not in title else ""),
            "description": "\n".join(lines), "tags": (G["base_tags"] + ents)[:15]}
