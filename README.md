# ClipX

ClipX turns long gameplay videos into finished YouTube Shorts and videos, and posts them for you.

It finds source videos, downloads them, picks the most exciting moments, edits them (titles, captions, slow motion,
transitions, sound effects, creator credit), checks every clip for glitches, writes titles and descriptions, and
uploads to YouTube on a schedule. It was built for a GTA 6 channel, but the themes are just a list you can change.

**See the results:** every Short and video on this channel was made and posted with ClipX:
**[GTA VI Radar on YouTube](https://www.youtube.com/@gta-vi-leaks-ps5)**

Everything is free: Python, ffmpeg, yt-dlp and the free YouTube API quota. No paid service and no GPU are needed.
No AI model is needed to run it either; moments are picked with plain audio and motion maths.

> **Read this before you use it.** Clipping other people's videos can get your uploads claimed, blocked or your
> channel struck, and "credit to the creator" is not permission. Downloading from YouTube may also break YouTube's
> terms. ClipX records where every clip came from and refuses known publisher footage, but it cannot make reuse
> legal. Use your own footage, footage you have permission for, or accept the risk knowingly.

---

## What it does, step by step

| Step | What happens | Main file |
|---|---|---|
| 1. Find sources | Searches YouTube for each theme (chases, fights, glitches, free roam...) and keeps raw gameplay, skipping news and explainer videos | `clipx/factory.py plan`, `clipx/discover.py` |
| 2. Check rights | Every source gets a status: blocked (official publisher), Creative Commons, own, permission, or third-party | `clipx/rights.py`, `clipx/guard.py` |
| 3. Download | Fetches each source at up to 1080p and saves who made it | `clipx/factory.py feed` |
| 4. Pick moments | Finds the loudest, fastest-moving moments in each source, at least 45 seconds apart | `clipx/factory.py` (`peaks`) |
| 5. Plan clips | Writes one small JSON "recipe" per clip: which seconds to use, on-screen title, captions, effects | `factory/specs/*.json` |
| 6. Edit | Renders the recipe into a finished Short (1080x1920) or video (1920x1080) | `clipx/pro.py` |
| 7. Quality check | Rejects clips with dark frames, blank/menu frames, white flashes or one-frame glitches | `clipx/qa.py` |
| 8. Thumbnails and text | Makes a thumbnail for each long video, plus title, description and tags for every clip | `clipx/thumb.py`, `factory/meta/*.json` |
| 9. Upload safely | Uploads as private first, publishes only if YouTube shows no block | `clipx/uploader.py` |
| 10. Schedule | Fills fixed daily time slots (for example 11:00 and 17:00) far ahead, a few uploads per day | `work/fl/sched_next.py` |

What a finished Short looks like: a 2-second slow-motion teaser of the best moment, a quick transition, then the
40-second scene with a two-line title on top, timed captions, sound effects and a "via creator" credit.

---

## Setup

Tested on Windows 11 with Python 3.13. It should work on macOS and Linux for the Python parts; the helper scripts in
`work/fl/*.ps1` are PowerShell and have the path `D:\Jayant\ClipX` written into them, so change that path to yours.

### 1. Install the tools

1. **Python 3.11 or newer**: https://www.python.org/downloads/ (tick "Add Python to PATH").
2. **ffmpeg** (includes ffprobe): https://ffmpeg.org/download.html. Make sure `ffmpeg -version` works in a terminal.
3. **Node.js** (yt-dlp needs a JavaScript runtime for YouTube): https://nodejs.org/
4. Get the code and install the Python packages:

```powershell
git clone <your-repo-url> ClipX
```

```powershell
cd ClipX
```

```powershell
pip install -r requirements.txt
```

### 2. Connect your YouTube channel (needed for searching and uploading)

1. Go to https://console.cloud.google.com/ and create a project.
2. Enable **YouTube Data API v3** for it.
3. Set up the **OAuth consent screen**. Add your own Google account as a test user. Note: while the project is in
   "Testing" mode, Google signs you out every 7 days; publish the app to "Production" to avoid that.
4. Create **OAuth client ID** credentials of type **Desktop app** and download the JSON file.
5. Save it as `secrets/client_secret.json` in the project.
6. Sign in once (a browser window opens):

```powershell
python -m clipx.uploader auth
```

This creates `secrets/token.json`. **Never share or commit anything in `secrets/`.** The included `.gitignore` keeps it out of git.

### 3. Optional: cookies for downloading

After a few dozen downloads YouTube may answer "Sign in to confirm you're not a bot". If that happens, export your
YouTube cookies (Netscape format) from a private browser window and save them as `secrets/youtube_cookies.txt`.
ClipX uses the file automatically when it exists. Treat it like a password.

### 4. Optional extras

- `models/` holds two small detection models (face and person) used for webcam avoidance and player tracking. See `models/ATTRIBUTION.md`.
- Put royalty-free `.mp3` files in `assets/music` if you want a music bed in the older edit styles.

---

## Quick start: make a big batch

Run these from the project folder.

```powershell
python -m clipx.factory plan
```
Searches every theme and writes the list of sources to `factory/sources.json`. Each search uses 100 of your 10,000 daily API units.

```powershell
python -m clipx.factory feed
```
Downloads the sources one by one, finds the best moments and writes the clip recipes. It pauses between downloads
and stops by itself if YouTube starts blocking; run it again later and it continues.

```powershell
python -m clipx.factory work
```
Renders and quality-checks the clips. Start it in two or three terminals at once to use more CPU cores. Shorts are done first.

```powershell
python -m clipx.factory status
```
Shows how many sources are fetched and how many clips are rendered, rejected or failed.

Other factory commands: `unlock` (after a crash or restart, releases half-finished clips so they are redone),
`reshape` (keeps 20 long videos and turns the rest of the planned videos into Shorts), `reset` (parks the current run and starts clean).

On a 10-core laptop CPU a 42-second Short takes about 5 to 10 minutes with three workers running.

---

## Posting

**Safe flow (recommended).** Nothing goes public until YouTube has had time to check it.

```powershell
python -m clipx.uploader post --n 3
```
Uploads the next 3 queued clips as **private**.

```powershell
python -m clipx.uploader release
```
Run about 10 minutes later. Publishes the ones YouTube processed without a block and flags the rest.

```powershell
python -m clipx.uploader health
```
Re-checks everything already posted (views, blocks).

Other commands: `status`, `pause`, `resume`, `post --dry-run` (shows what would be uploaded), `post --direct` (public immediately, no safety check).

**Automatic schedule.** `work/fl/sched_next.py` fills fixed daily slots with the finished Shorts, rotating through the themes:

```powershell
python work\fl\sched_next.py pick 6
```
Shows which Shorts would go next, without uploading.

```powershell
python work\fl\sched_next.py auto
```
Uploads up to the daily limit, gives each Short the earliest free slot (11:00 and 17:00 by default, edit `TIMES` at
the top of the file), and checks that nothing already scheduled got blocked.

`work/fl/daily_schedule.ps1` runs that every hour and writes one result line per run to `factory/schedule.log`. Put a
shortcut to it in your Windows Startup folder and the schedule keeps itself filled whenever the PC is on. Scheduled
clips publish from YouTube's servers, so they go out even when your PC is off.

**The real limit is the API quota.** One upload costs about 1,600 of the 10,000 free units per day, so about 6 uploads
a day. Uploading 6 while publishing 2 keeps the schedule growing ahead. You can ask Google for more quota for free.

---

## Making one clip by hand

Every clip is a JSON recipe. Copy one from `specs/` (for example `specs/chasecrash.json`), change it, and render:

```powershell
python -m clipx.pro specs\chasecrash.json
```

```powershell
python -m clipx.qa output\pro_chasecrash.mp4
```

The main fields:

| Field | Meaning |
|---|---|
| `kind` | `short` or `video` |
| `src` | the source video file |
| `title` | two lines of on-screen title |
| `pieces` | the cuts: start `s`, end `e`, optional `speed` (0.5 = slow motion), `cx` (horizontal crop position), `zoom`, `tr` (transition: `whip` or `fade`) |
| `caps` | captions: piece number `p`, seconds into it `t`, duration `d`, `text` |
| `flash`, `sfx` | flash and sound-effect hits |
| `vcrop`, `vy` | crop away baked-in watermarks or subtitles |
| `facecam`, `auto_exposure` | set to `false` to turn off webcam avoidance or the dark-footage lift |
| `credit` | overrides the on-screen "via ..." line |
| `"cx": "track"` | Shorts only: the crop follows the player (slow on CPU) |

Set the environment variable `CLIPX_ENCODER=qsv` to encode with Intel Quick Sync instead of the default software encoder.

---

## Other tools in the box

| Command | What it does |
|---|---|
| `python -m clipx.discover "GTA 6 fight" --n 15` | Find source videos with their rights status (`--cc` = Creative Commons only) |
| `python -m clipx.rights check <id-or-url>` | Show or record who owns a source (`mark <id> own --note "proof"`, `list`) |
| `python -m clipx.run "<link or file>"` | Older one-command pipeline: transcribe a video, pick moments by speech, edit and queue |
| `python -m clipx.montage "<file>" --kind short --dur 45` | Beat-synced montage with real transitions |
| `python -m clipx.explainer scripts\<name>.json` | Original Short with AI voice and graphics, no game footage |
| `python -m unittest discover tests` | Run the unit tests |

---

## Folders

| Folder | What is in it | In git? |
|---|---|---|
| `clipx/` | The program | yes |
| `specs/`, `scripts/` | Hand-written clip recipes and explainer scripts | yes |
| `tests/`, `docs/`, `models/` | Tests, notes, detection models | yes |
| `work/fl/` | Helper scripts (start/stop workers, scheduler, cleanup) | scripts only |
| `work/` | Downloaded sources and their credit files | no |
| `factory/` | State of a batch run: sources, recipes, logs | no |
| `output/` | Finished clips not yet posted; `output/posted/` = uploaded ones | no |
| `other/` | Thumbnails, credit records, rejected clips, render leftovers | no |
| `secrets/` | Google sign-in and cookies. **Never commit.** | no |
| `queue.json`, `rights.json` | Upload queue and source-rights ledger (your channel's own state) | no |

---

## Using an AI coding assistant (Claude or others)

You do not need any AI to run ClipX: every step above is a normal command.

An AI coding assistant is useful for the parts around it: writing clip recipes, starting and watching long runs,
fixing errors, and reviewing frames before posting. This project was built and operated with **Claude Code**, and
`CLAUDE.md` holds the working rules for it (never post without approval, keep `output/` clean, run QA on every render,
never print `secrets/`).

Other assistants that can read a repository and run terminal commands should work the same way, for example
**OpenAI Codex CLI, Gemini CLI, Cursor, GitHub Copilot (agent mode), Windsurf, Cline or Aider**. They have not been
tested with this project. Most of them look for their own instruction file instead of `CLAUDE.md` (commonly
`AGENTS.md`, or `GEMINI.md` for Gemini CLI), so copy the rules from `CLAUDE.md` into the file your tool reads.

---

## Known limits and lessons

- **Copyright.** Third-party recordings can be claimed days after upload. Official publisher footage is blocked outright.
- **Repetitive content.** Hundreds of similar Shorts with numbered titles can be flagged by YouTube and hurt monetisation. Review clips before scheduling months of them.
- **Captions are generic per theme.** They are not written from what is on screen, so some will not match the scene.
- **Lower-ranked moments are weaker.** The first two moments of a source are usually good; the tenth often is not.
- **QA is automatic only.** It catches broken frames, not boring clips. Look at a frame sheet before posting anything important.
- **Bot checks.** YouTube blocks downloads after a few dozen in a row; cookies and a pause between downloads help.
- **Heavy sources are slow.** 4K, 60 fps and AV1 files take two to three times longer to cut than 1080p 30 fps.
- **Keep the PC awake.** Sleep stops rendering; workers do not restart by themselves after a reboot (run `factory unlock`, then start them again).
- **CPU only.** Intel Quick Sync encoding works but was not faster here; the slow part is the zoom and scaling, not the encode.

## Credits

Built with ffmpeg, yt-dlp, OpenCV, faster-whisper, ONNX Runtime, Pillow, NumPy, edge-tts and the YouTube Data API.
