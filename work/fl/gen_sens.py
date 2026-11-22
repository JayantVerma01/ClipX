import json
from pathlib import Path
Path("specs").mkdir(exist_ok=True)


def short(slug, src, title, cold, mains, caps, vy=0.3, cx=0.5, last_src=None):
    pcs = [{"s": cold[0], "e": cold[1], "speed": 0.5, "cx": cx, "zoom": "in"}]
    for i, (s, e) in enumerate(mains):
        pcs.append({"s": s, "e": e, "cx": cx, "zoom": "out" if i % 2 == 0 else "in", "tr": "whip" if i == 0 else "fade"})
    if last_src:
        pcs[-1]["src"] = last_src
    spec = {"slug": slug, "kind": "short", "src": f"work/{src}.mp4", "tag": "GTA 6", "layout": "tall", "title": title,
            "vcrop": 0.8, "vy": vy, "pieces": pcs, "caps": [{"p": p, "t": t, "d": d, "text": x} for p, t, d, x in caps],
            "flash": [{"p": 1, "t": 0.0}], "sfx": [{"p": 0, "t": 0.05, "k": "impact"}]}
    Path(f"specs/{slug}.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")


short("sens_dancefloor", "RSy0UkR0JBs", ["DANCE FLOOR", "TURNS STEAMY"], (231.0, 233.0), [(181, 190), (196, 208), (229, 242)],
      [(0, .3, 2.0, "WAIT FOR IT"), (1, .5, 2.4, "IT STARTS WITH A DANCE"), (1, 5, 2.4, "SHE PULLS HIM CLOSER"),
       (2, .5, 2.4, "THE MUSIC GETS LOUDER"), (2, 7, 2.8, "NO ONE IS WATCHING"), (3, .5, 2.6, "THEN THE LIGHTS TURN RED"),
       (3, 8, 3.2, "THE NIGHT IS JUST BEGINNING")], vy=0.12)
short("sens_firstnight", "ID-C0E_DidA", ["JASON MEETS", "LUCIA"], (153.0, 155.0), [(112, 140), (148, 157)],
      [(0, .3, 2.0, "THAT LOOK"), (1, .5, 2.8, "A STOLEN CAR. A STRANGER."), (1, 8, 3.0, "TWO PEOPLE WHO JUST MET"),
       (1, 16, 2.6, "THE TENSION IS REAL"), (2, .5, 2.6, "SHE IS NOT SCARED"), (2, 4.5, 3.4, "LET'S GO HAVE SOME FUN")], vy=0.12)
short("sens_yacht", "boNEXq35Hg0", ["YACHT DAY", "GOLDEN HOUR"], (265.0, 267.0), [(264, 290), (297, 310), (335, 346)],
      [(0, .3, 2.4, "GOLDEN HOUR HITS DIFFERENT"), (1, .5, 2.6, "A YACHT. A SUNSET."), (1, 8, 2.4, "GOOD VIBES ONLY"),
       (1, 16, 2.8, "NOBODY'S IN A HURRY"), (2, .5, 3.2, "THE CONVERSATION GETS INTERESTING"),
       (3, .5, 2.8, "ONE LAST LOOK AT THE CITY"), (3, 6, 2.8, "WELCOME TO VICE CITY")], vy=0.3)
short("sens_nightclub", "boNEXq35Hg0", ["NINE1NINE", "AFTER DARK"], (145.5, 147.5), [(159, 171), (178, 192), (205, 214)],
      [(0, .3, 2.0, "FEEL THE BASS"), (1, .5, 2.4, "VICE CITY NIGHTLIFE"), (1, 6, 3.0, "CLOSER AND CLOSER"),
       (2, .5, 2.6, "THEN THE VIP LOUNGE"), (2, 7, 3.4, "WHAT HAPPENS HERE STAYS HERE"),
       (3, .5, 3.0, "THE NIGHT NEVER ENDS")], vy=0.12, last_src="work/RSy0UkR0JBs.mp4")

V = "work/ID-C0E_DidA.mp4"; R = "work/RSy0UkR0JBs.mp4"; B = "work/boNEXq35Hg0.mp4"
wins = [(V, 118, 140), (V, 148, 157), (R, 181, 190), (R, 196, 208), (R, 229, 242), (B, 159, 171), (B, 178, 192),
        (B, 264, 290), (B, 297, 310), (B, 335, 346)]
pcs = [{"src": s, "s": a, "e": b, "cx": 0.5, "zoom": "in" if i % 2 == 0 else "out", "tr": "fade"} for i, (s, a, b) in enumerate(wins)]
caps = [(0, .5, 3, "A STOLEN CAR. A STRANGER."), (1, .5, 3, "LET'S GO HAVE SOME FUN"), (2, .5, 3, "THE DANCE FLOOR"),
        (3, .5, 3, "SHE PULLS HIM CLOSER"), (4, .5, 3, "THEN THE LIGHTS TURN RED"), (5, .5, 3, "NINE1NINE AFTER DARK"),
        (6, .5, 3, "THE VIP LOUNGE"), (7, .5, 3, "A YACHT. A SUNSET."), (8, .5, 3, "GOLDEN HOUR HITS DIFFERENT"),
        (9, .5, 3, "WELCOME TO VICE CITY")]
spec = {"slug": "sens_vcafterdark", "kind": "video", "src": R, "tag": "GTA 6", "vcrop": 0.8, "vy": 0.3,
        "title": ["VICE CITY", "AFTER DARK"], "pieces": pcs, "caps": [{"p": p, "t": t, "d": d, "text": x} for p, t, d, x in caps],
        "flash": [], "sfx": []}
Path("specs/sens_vcafterdark.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
print("sensual specs written")
