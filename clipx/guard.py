"""Copyright safety check: warn before processing footage owned by publishers that block reuploads via Content ID."""
import re

# Channels/owners that actively claim their footage (video + music). Add more as you learn.
RESTRICTED = ["rockstar games", "take-two", "take two", "2k", "playstation", "xbox", "ign", "gamespot",
              "official", "vevo", "warner", "sony", "universal", "netflix", "disney", "ubisoft", "ea ",
              "electronic arts", "activision", "nintendo", "bethesda", "valve"]
WARNING = """
==================  COPYRIGHT WARNING  ==================
Source channel : {channel}
Source title   : {title}

This looks like OFFICIAL publisher content. Re-uploading cuts of it is usually blocked by Content ID
(your first test Short was blocked worldwide for exactly this reason). Expect: blocked videos or
claims with no ads, and repeated problems can hurt the channel.

Safer sources: your own gameplay, footage you have written permission for, or content explicitly
licensed for reuse.

If you really have the rights, run again with:  --i-have-rights
==========================================================
"""


def check(meta, allow=False):
    """meta = {'channel','title',...}. Returns None if fine; raises SystemExit with a warning if restricted."""
    hay = f"{meta.get('channel') or ''} {meta.get('title') or ''}".lower()
    hit = [k for k in RESTRICTED if re.search(r"\b" + re.escape(k.strip()) + r"\b", hay)]
    if hit and not allow:
        raise SystemExit(WARNING.format(channel=meta.get("channel"), title=meta.get("title")))
    if hit:
        print("WARNING: restricted-looking source, continuing because --i-have-rights was set.")
