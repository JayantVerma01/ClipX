import json
from pathlib import Path
Path("specs").mkdir(exist_ok=True)


def short(slug, src, title, cold, mains, caps, cx=0.5, flash=True):
    pcs = [{"s": cold[0], "e": cold[1], "speed": 0.5, "cx": cx, "zoom": "in"}]
    for i, (s, e) in enumerate(mains):
        pcs.append({"s": s, "e": e, "cx": cx, "zoom": "out" if i % 2 == 0 else "in", "tr": "whip" if i == 0 else "fade"})
    spec = {"slug": slug, "kind": "short", "src": f"work/{src}.mp4", "tag": "GTA 6", "layout": "tall", "title": title,
            "pieces": pcs, "caps": [{"p": p, "t": t, "d": d, "text": x} for p, t, d, x in caps],
            "flash": [{"p": 1, "t": 0.0}] if flash else [], "sfx": [{"p": 0, "t": 0.05, "k": "impact"}]}
    Path(f"specs/{slug}.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")


def video(slug, src, title, wins, caps, cx=0.3, vcrop=0.9):
    pcs = [{"s": s, "e": e, "cx": cx, "zoom": "in" if i % 2 == 0 else "out", "tr": "fade"} for i, (s, e) in enumerate(wins)]
    spec = {"slug": slug, "kind": "video", "src": f"work/{src}.mp4", "tag": "GTA 6", "vcrop": vcrop, "title": title,
            "pieces": pcs, "caps": [{"p": p, "t": t, "d": d, "text": x} for p, t, d, x in caps], "flash": [], "sfx": []}
    Path(f"specs/{slug}.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")


# ---------------- SHORTS ----------------
short("chasecrash", "9TLwyuGDSmI", ["POLICE CHASE", "GONE WRONG"], (197.0, 199.0), [(186, 204), (144, 156), (336, 346)],
      [(0, .3, 2.2, "FULL SPEED"), (1, .5, 2.4, "NOTHING CAN STOP HIM"), (1, 8, 2.4, "STRAIGHT THROUGH TRAFFIC"),
       (1, 14, 2.6, "THEN HE BAILS OUT"), (2, .5, 2, "ROUND TWO"), (2, 6, 2.6, "COPS EVERYWHERE"),
       (3, .5, 2.4, "THE CHASE GOES ON"), (3, 6, 2.6, "THIS IS GTA 6")])
short("trafficchaos", "9TLwyuGDSmI", ["TRAFFIC CHAOS", "IN LEONIDA"], (482.0, 484.0), [(466, 490), (114, 130)],
      [(0, .3, 2, "WATCH THIS"), (1, .5, 2.4, "THE ROAD LOOKS CLEAR"), (1, 9, 2.4, "THEN A HUGE TRUCK"),
       (1, 18, 2.4, "TOTAL CHAOS"), (2, .5, 2.4, "SIRENS EVERYWHERE"), (2, 8, 2.6, "ANYTHING CAN HAPPEN")])
short("jettheft", "6E2cBXFCDyQ", ["STEALING A", "MILITARY JET"], (518.0, 520.0), [(355, 367), (382, 392), (513, 528)],
      [(0, .3, 2.2, "HE ACTUALLY DID IT"), (1, .5, 2.8, "SNEAKING INTO A MILITARY BASE"), (1, 6, 2.6, "NO PLAN. NO FEAR."),
       (2, .5, 2.4, "THEN IT GOES WRONG"), (2, 5, 1.6, "BOOM"), (3, .5, 2.4, "BUT THE JET IS HIS"),
       (3, 7, 2.2, "FULL THROTTLE")], cx=0.45)
short("subwayshootout", "BgO-5PVOj5c", ["SUBWAY", "SHOOTOUT"], (194.0, 196.5), [(6, 16), (152, 170), (236, 250)],
      [(0, .3, 2.2, "LOCKED ON"), (1, .5, 2.8, "A QUIET DAY AT THE STATION"), (1, 5.5, 2.2, "UNTIL IT ISN'T"),
       (2, .5, 2.4, "THEN GUNS COME OUT"), (2, 9, 2.4, "NO WAY OUT"), (3, .5, 2.2, "TAKING COVER"),
       (3, 6, 2.6, "EVERY STEP COUNTS")])
short("tankvspolice", "-UuHA1h-Cf8", ["TANK VS", "THE POLICE"], (383.5, 385.5), [(338, 352), (377, 391), (511, 525)],
      [(0, .3, 1.6, "BOOM"), (1, .5, 2.0, "ONE TANK"), (1, 4, 2.0, "SIX STARS"), (1, 8, 2.4, "COPS EVERYWHERE"),
       (2, .5, 2.4, "THEY KEEP COMING"), (2, 7, 2.6, "EXPLOSIONS EVERYWHERE"), (3, .5, 2.2, "STILL STANDING"),
       (3, 7, 2.6, "BUT FOR HOW LONG")])
short("beachrampage", "8-DRGbQ1IXc", ["5-STAR CHASE", "ON THE BEACH"], (376.0, 378.0), [(369, 383), (74, 88), (184, 196)],
      [(0, .3, 2, "THAT HIT HURT"), (1, .5, 2.6, "FIVE STARS ON THE SAND"), (1, 6, 2.4, "NO ROADS NEEDED"),
       (2, .5, 2.6, "THROUGH THE PROMENADE"), (2, 7, 2.4, "CROWDS SCATTER"), (3, .5, 2.4, "BACK ON THE BEACH"),
       (3, 6, 2.2, "KEEP MOVING")])
short("nightfight", "bfY0coYanSg", ["NIGHT FIGHT", "IN VICE CITY"], (72.0, 74.0), [(60, 80), (112, 132)],
      [(0, .3, 1.8, "ONE SWING"), (1, .5, 2.2, "A NORMAL NIGHT"), (1, 6, 3.0, "THEN THE WHOLE YARD EXPLODES"),
       (1, 14, 2.6, "EVERYONE JOINS IN"), (2, .5, 2.0, "ROUND TWO"), (2, 7, 2.4, "FISTS EVERYWHERE"),
       (2, 12.5, 3.0, "THEN THE COPS SHOW UP")])
short("cruiseship", "OnWC__OxyTk", ["CRUISE SHIP", "MAYHEM"], (186.0, 188.0), [(181.7, 191), (107, 121), (43, 57)],
      [(0, .3, 2.2, "FIGHT ON DECK"), (1, .4, 2.6, "A CRUISE SHIP. NO RULES."), (1, 4.5, 3.0, "CREW MEMBERS FIGHT BACK"),
       (2, .5, 3.0, "THEN A HELICOPTER SHOWS UP"), (2, 8, 2.4, "LANDING ON THE ROOF"), (3, .5, 2.2, "ROOFTOP PARKOUR"),
       (3, 7, 2.4, "ONE WRONG STEP")])
short("sixstars", "ORYwlJXszi4", ["6 STARS", "THE ARMY ARRIVES"], (118.0, 120.0), [(172, 185), (74, 88), (111, 124)],
      [(0, .3, 1.6, "BOOM"), (1, .5, 2.4, "SKY HIGH CHAOS"), (1, 6, 2.6, "NO ONE IS SAFE"),
       (2, .5, 2.4, "TANKS ON THE GROUND"), (2, 7, 2.4, "NOTHING SURVIVES"), (3, .5, 2.4, "FIRE EVERYWHERE"),
       (3, 7, 3.0, "GTA 6 GOES ALL OUT")])

# ---------------- VIDEOS ----------------
video("v_beachrampage", "8-DRGbQ1IXc", ["5-STAR RAMPAGE", "VICE OCEAN BEACH"], [(55, 95), (183, 200), (215, 240), (365, 395), (400, 420)],
      [(0, .5, 3, "FIVE STARS ON THE BEACH"), (1, .5, 3, "NO ROADS NEEDED"), (2, .5, 3, "THE POLICE KEEP COMING"),
       (3, .5, 3, "IT GETS WILDER"), (4, .5, 3, "AND THEN THE AMBULANCE")])
video("v_policechase", "9TLwyuGDSmI", ["OPEN WORLD", "POLICE CHASE"], [(96, 135), (140, 160), (186, 206), (330, 350), (466, 490)],
      [(0, .5, 3, "THE CHASE BEGINS"), (1, .5, 3, "COPS ON ALL SIDES"), (2, .5, 3, "STRAIGHT THROUGH TRAFFIC"),
       (3, .5, 3, "STILL NO ESCAPE"), (4, .5, 3, "TOTAL CHAOS")], cx=0.5, vcrop=0.95)
video("v_tankvspolice", "-UuHA1h-Cf8", ["TANK VS 6 STARS", "CAN IT SURVIVE?"], [(15, 40), (335, 360), (375, 400), (460, 485), (508, 533)],
      [(0, .5, 3, "ONE TANK. SIX STARS."), (1, .5, 3, "THE FIRST EXPLOSIONS"), (2, .5, 3, "THEY KEEP COMING"),
       (3, .5, 3, "ON THE RUN"), (4, .5, 3, "THE FINAL STAND")], cx=0.5, vcrop=0.95)
video("v_cruiseship", "OnWC__OxyTk", ["CRUISE SHIP", "MAYHEM"], [(5, 25), (40, 60), (105, 125), (130, 150), (181.7, 195), (215, 232)],
      [(0, .5, 3, "BOARDING THE SHIP"), (1, .5, 3, "ROOFTOP PARKOUR"), (2, .5, 3, "A HELICOPTER ON DECK"),
       (3, .5, 3, "NO ONE IS SAFE"), (4, .5, 3, "FIGHT ON DECK"), (5, .5, 3, "SHOTS FIRED")], cx=0.5, vcrop=0.95)
video("v_subway", "BgO-5PVOj5c", ["SUBWAY", "SHOOTOUT"], [(0, 25), (75, 95), (150, 175), (185, 200), (236, 255), (300, 318)],
      [(0, .5, 3, "A QUIET DAY AT THE STATION"), (1, .5, 3, "ON THE TRAIN"), (2, .5, 3, "THEN GUNS COME OUT"),
       (3, .5, 3, "LOCKED ON"), (4, .5, 3, "TAKING COVER"), (5, .5, 3, "THE ESCAPE")], cx=0.5, vcrop=0.95)
video("v_sixstars", "ORYwlJXszi4", ["6 STARS", "THE ARMY ARRIVES"], [(66, 90), (106, 128), (168, 190), (278, 300), (308, 326), (334, 352)],
      [(0, .5, 3, "TANKS ON THE RUNWAY"), (1, .5, 3, "EXPLOSIONS EVERYWHERE"), (2, .5, 3, "FIGHTER JETS"),
       (3, .5, 3, "ON THE GROUND"), (4, .5, 3, "THE CHASE"), (5, .5, 3, "THE AFTERMATH")], cx=0.5, vcrop=0.95)
video("v_beachbrawls", "gPCd2SD5X3k", ["BEACH BRAWLS", "NPCS FIGHT BACK"], [(80, 100), (413, 445), (698, 726), (760, 780), (814, 832), (845, 860)],
      [(0, .5, 3, "WELCOME TO OCEAN BEACH"), (1, .5, 3, "IT STARTS WITH A PUSH"), (2, .5, 3, "ROUND TWO"),
       (3, .5, 3, "THE CROWD WATCHES"), (4, .5, 3, "AND KEEPS GOING"), (5, .5, 3, "THE BEACH SETTLES DOWN")])
video("v_jasonlucia", "bfY0coYanSg", ["JASON & LUCIA", "FIGHTS, FLIRTS & TROUBLE"], [(0, 22), (60, 82), (112, 132), (148, 166), (280, 300)],
      [(0, .5, 3, "A TENSE POOL HALL"), (1, .5, 3, "THE NIGHT TURNS VIOLENT"), (2, .5, 3, "THEN THE POLICE ARRIVE"),
       (3, .5, 3, "KEEP MOVING"), (4, .5, 3, "THE CHEMISTRY IN THE KITCHEN")], cx=0.5, vcrop=0.95)
print(len(list(Path("specs").glob("*.json"))), "specs")
