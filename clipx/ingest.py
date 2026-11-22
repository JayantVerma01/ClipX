"""Download + transcribe. Everything is cached by video id so nothing is done twice."""
import json
import shutil
import subprocess
import sys
from .config import WORK


def download(url: str) -> tuple[str, "Path"]:
    import yt_dlp
    WORK.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": "bv*[height<=2160]+ba/b[height<=2160]",
        "merge_output_format": "mp4",
        "outtmpl": str(WORK / "%(id)s.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "continuedl": True,
        "live_from_start": True,
    }
    if not shutil.which("deno") and shutil.which("node"):    # yt-dlp needs a JS runtime for full YouTube support
        opts["js_runtimes"] = {"node": {}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    vid = info["id"]
    meta = {"id": vid, "title": info.get("title"), "channel": info.get("channel"),
            "url": url, "duration": info.get("duration"), "channel_id": info.get("channel_id"),
            "license": info.get("license"), "view_count": info.get("view_count"), "was_live": info.get("was_live")}
    (WORK / f"{vid}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return vid, WORK / f"{vid}.mp4"


def transcribe(vid: str, video, language: str = "en") -> list[dict]:
    """Returns [{start,end,text,words:[{w,s,e}], lang, caption_language}]. Cached as JSON.
    language: "en" = fast English-only model (default, unchanged behaviour);
              "auto" = multilingual model, detects the language, Hindi becomes Hinglish (see clipx.lang);
              "hi" / other code = force that language."""
    from . import lang as L
    suffix = "" if language == "en" else f".{language}"
    cache = WORK / f"{vid}.transcript{suffix}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    from faster_whisper import WhisperModel
    from .config import WHISPER_MODEL, WHISPER_MULTI
    model = WhisperModel(WHISPER_MODEL if language == "en" else WHISPER_MULTI, device="cpu", compute_type="int8", cpu_threads=8)
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    if language == "en":
        segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=1, language="en")
        spoken = "en"
    else:
        # decide the language once from the first ~2 minutes, then lock it for the whole video (avoids per-chunk flips)
        lock = L.LanguageLock(forced=None if language == "auto" else language)
        _, probe = model.transcribe(audio[: 16000 * 120], language=None if language == "auto" else language, beam_size=1)
        lock.vote(probe.language, getattr(probe, "language_probability", 1.0) or 1.0)
        spoken = language if language != "auto" else (probe.language or "unknown")
        segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=1, language=spoken)
    out = []
    for s in segs:
        words = [{"w": w.word.strip(), "s": w.start, "e": w.end} for w in (s.words or [])]
        text = s.text.strip()
        if spoken == "hi":
            words = [{**w, "w": L.romanize_hindi(w["w"]) if L.has_devanagari(w["w"]) else w["w"]} for w in words]
            text = L.romanize_hindi(text) if L.has_devanagari(text) else text
        cap, why = L.caption_language(spoken, " ".join(w["w"] for w in words))
        out.append({"start": s.start, "end": s.end, "text": text, "words": words, "lang": spoken,
                    "caption_language": cap, "caption_note": why})
        print(f"\r  transcribed {s.end/60:.1f} min", end="", file=sys.stderr)
    print(file=sys.stderr)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


def audio_energy(video) -> "np.ndarray":
    """Per-second loudness (RMS) via ffmpeg -> numpy. No extra deps."""
    import numpy as np
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000",
                        "-f", "s16le", "-"], capture_output=True, check=True)
    a = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768
    n = len(a) // 8000
    return np.sqrt((a[: n * 8000].reshape(n, 8000) ** 2).mean(axis=1))
