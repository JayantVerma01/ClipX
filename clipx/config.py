from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"        # downloads, transcripts (cached, never redone)
OUT = ROOT / "output"       # ONLY finished, not-yet-posted .mp4 files live here
POSTED = OUT / "posted"     # a clip is moved here the moment it is posted
AUX = ROOT / "other"        # everything else: subtitle/filter/sfx files, thumbnails, raw cuts
RAW = AUX / "raw"          # raw cuts + manifests (intermediate)
for _d in (OUT, POSTED, AUX, AUX / "thumbs", RAW):
    _d.mkdir(parents=True, exist_ok=True)

SHORT = (40, 90)            # seconds
VIDEO = (120, 300)          # seconds

WHISPER_MULTI = "small"     # multilingual model, used only with --lang auto/hi
WHISPER_MODEL = "small.en"  # CPU friendly; use "base.en" for speed, "medium.en" for accuracy
MAX_CLIPS_PER_SOURCE = 12

HYPE_WORDS = {
    "gta", "vice", "city", "lucia", "jason", "leonida", "rockstar", "trailer", "insane", "crazy",
    "wow", "omg", "unbelievable", "incredible", "look", "huge", "massive", "secret", "leak",
    "new", "first", "confirmed", "finally", "best", "worst", "never", "boom", "fire", "chase",
}
