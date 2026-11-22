"""Titles / descriptions / tags for the finished pro clips. Run: python work\\fl\\metadata.py [slug ...]  -> enqueues them.
Nothing is uploaded here; `python -m clipx.uploader post` does that (private first)."""
import sys
sys.path.insert(0, ".")
from clipx import uploader

DIS = ("Not affiliated with or endorsed by Rockstar Games or Take-Two Interactive. "
       "Grand Theft Auto is a trademark of Take-Two Interactive Software, Inc.")
BASE = ["GTA 6", "GTA VI", "GTA 6 gameplay", "Grand Theft Auto VI", "Vice City", "Rockstar Games", "gta6"]

# slug: (title, hook line + question, extra tags)
SHORTS = {
    "chasecrash": ("GTA 6 Police Chase Goes WRONG (Full Speed Crash) #Shorts", "A full-speed police chase through Leonida ends in a pile-up. Would you have made that turn?", ["GTA 6 police chase", "GTA 6 crash"]),
    "jettheft": ("Stealing a Military JET in GTA 6 #Shorts", "Breaking into the military base and flying out in a fighter jet. Would you try this first?", ["GTA 6 jet", "GTA 6 military base"]),
    "subwayshootout": ("GTA 6 Subway Shootout - No Way Out #Shorts", "A quiet station turns into a shootout. How would you escape?", ["GTA 6 shootout", "GTA 6 subway"]),
    "tankvspolice": ("TANK vs Police in GTA 6 (6 Stars) #Shorts", "One tank against a 6-star wanted level. How long would you last?", ["GTA 6 tank", "GTA 6 6 stars"]),
    "beachrampage": ("5-Star Police Chase ON THE BEACH in GTA 6 #Shorts", "Five stars, no roads, just sand. Best escape route?", ["GTA 6 beach", "GTA 6 wanted level"]),
    "nightfight": ("GTA 6 Night Fight Gets Out Of Hand #Shorts", "One swing and the whole yard joins in, then the cops arrive. Who started it?", ["GTA 6 fight", "GTA 6 Jason"]),
    "cruiseship": ("Cruise Ship MAYHEM in GTA 6 #Shorts", "Fights on deck, a helicopter on the roof and rooftop parkour. What would you do on the ship?", ["GTA 6 cruise ship", "GTA 6 helicopter"]),
    "sixstars": ("What 6 STARS Looks Like in GTA 6 #Shorts", "Tanks, jets and explosions: the army shows up at six stars. Could you survive?", ["GTA 6 6 stars", "GTA 6 army"]),
    "trafficchaos": ("GTA 6 Traffic Chaos - Truck vs Everyone #Shorts", "A clear road, then a huge truck. Total chaos. What's the worst crash you've had?", ["GTA 6 crash", "GTA 6 traffic"]),
    "sens_dancefloor": ("GTA 6 Dance Floor Turns STEAMY (Jason & Lucia) #Shorts", "The NINE1NINE dance floor heats up. Best couple in GTA history?", ["GTA 6 Lucia", "GTA 6 Jason", "GTA 6 nightclub"]),
    "sens_firstnight": ("The Night Jason Met Lucia - GTA 6 #Shorts", "A stolen car, a stranger and a lot of tension. Did you see this coming?", ["GTA 6 Lucia", "GTA 6 Jason", "GTA 6 cutscene"]),
    "sens_nightclub": ("GTA 6 Nightclub After Dark (NINE1NINE) #Shorts", "Vice City nightlife: neon, the dance floor and the VIP lounge. Would you visit?", ["GTA 6 nightclub", "GTA 6 nightlife"]),
    "sens_yacht": ("GTA 6 Yacht Party at Golden Hour #Shorts", "Sunset on a yacht in Vice City. Does this look next-gen to you?", ["GTA 6 yacht", "GTA 6 Lucia", "GTA 6 graphics"]),
}
VIDEOS = {
    "v_beachrampage": ("GTA 6: 5-Star Police Rampage on Vice Ocean Beach (Gameplay)", "A five-star wanted level across the promenade and the sand, ending with an ambulance getaway.", ["GTA 6 police chase", "GTA 6 beach", "GTA 6 wanted level"]),
    "v_policechase": ("GTA 6 Open World Police Chase - Crashes, Traffic & Chaos", "A long police chase through Leonida: pile-ups, on-foot escapes and total chaos on the highway.", ["GTA 6 police chase", "GTA 6 crash", "Leonida"]),
    "v_tankvspolice": ("Can a TANK Survive 6 Stars in GTA 6?", "One tank against the full six-star response: explosions, helicopters and a last stand.", ["GTA 6 tank", "GTA 6 6 stars"]),
    "v_cruiseship": ("GTA 6 Cruise Ship Mayhem - Fights, Parkour & a Helicopter", "Boarding the cruise ship: rooftop parkour, a helicopter landing, fights on deck and shots fired.", ["GTA 6 cruise ship", "GTA 6 helicopter"]),
    "v_subway": ("GTA 6 Subway Shootout - Full Scene", "A quiet day at the station turns into a running gunfight through the metro.", ["GTA 6 shootout", "GTA 6 subway", "GTA 6 Jason"]),
    "v_sixstars": ("What Happens at 6 STARS in GTA 6 (Army, Tanks & Jets)", "Tanks on the runway, fighter jets overhead and nowhere to hide: the six-star response.", ["GTA 6 6 stars", "GTA 6 army", "GTA 6 jet"]),
    "v_beachbrawls": ("GTA 6 Beach Brawls - NPCs Fight Back", "Ocean Beach fights from first push to full brawl, with the crowd reacting in real time.", ["GTA 6 fight", "GTA 6 NPC", "GTA 6 beach"]),
    "v_jasonlucia": ("GTA 6 Jason & Lucia - Fights, Flirting & Trouble", "A tense pool hall, a street brawl, the police, and the chemistry between Jason and Lucia.", ["GTA 6 Lucia", "GTA 6 Jason", "GTA 6 cutscene"]),
    "sens_vcafterdark": ("GTA 6 Vice City After Dark - Jason & Lucia's Night Out", "From a stolen car to the NINE1NINE dance floor to sunrise on a yacht: one night in Vice City.", ["GTA 6 Lucia", "GTA 6 Jason", "GTA 6 nightclub", "GTA 6 yacht"]),
}


def enqueue(slug):
    short = slug in SHORTS
    title, line, extra = (SHORTS if short else VIDEOS)[slug]
    desc = (line + ("\n\nTell me in the comments, and follow for more GTA 6 clips." if short else
                    "\n\nWhat was your favourite moment? Tell me in the comments, and subscribe for more GTA 6 clips.")
            + "\n\n" + DIS + "\n\n#GTA6 #GTAVI #ViceCity" + (" #Shorts" if short else ""))
    thumb = None if short else f"pro_{slug}_thumb.jpg"
    uploader.enqueue_pro(slug, title, desc, (BASE + extra)[:15], thumb=thumb, kind="short" if short else "video")
    print("queued", slug, "|", title)


if __name__ == "__main__":
    for s in sys.argv[1:]:
        enqueue(s)
