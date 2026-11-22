"""Step 1: URL or local file -> transcribe -> best moments -> raw cuts. Returns the manifest path."""
import json
import subprocess
from pathlib import Path
from .config import SHORT, VIDEO, OUT, RAW, WORK, MAX_CLIPS_PER_SOURCE
from . import ingest, moments


def process(src: str, kind="both", max_clips=MAX_CLIPS_PER_SOURCE, allow_restricted=False, lang="en", signals_on=True) -> Path:
    print("1/4 getting video...")
    if Path(src).is_file():
        path = Path(src)
        vid = "local_" + "".join(c if c.isalnum() else "_" for c in path.stem)[:40]
        print("  (local file: make sure you own it or have permission to use it)")
    else:
        from . import guard
        vid, path = ingest.download(src)
        guard.check(json.loads((WORK / f"{vid}.meta.json").read_text(encoding="utf-8-sig")), allow_restricted)
    print("2/4 transcribing (cached after first run)...")
    segs = ingest.transcribe(vid, path, lang)
    print("3/4 analysing audio + finding moments...")
    energy = ingest.audio_energy(path)
    ext = None
    if signals_on and not vid.startswith("local_"):
        from . import signals
        ext, used = signals.fetch(vid, len(energy))
        print("  audience signals:", ", ".join(used) if used else "none available for this video")
    kinds = {"short": SHORT, "video": VIDEO}
    todo = kinds if kind == "both" else {kind: kinds[kind]}
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    print("4/4 cutting...")
    for name, rng in todo.items():
        for i, (sc, st, en) in enumerate(moments.find_moments(segs, energy, rng, max_clips, external=ext), 1):
            out = RAW / f"{vid}_{name}{i:02d}_raw.mp4"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(st), "-to", str(en), "-i", str(path),
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", str(out)],
                           check=True)
            manifest.append({"file": out.name, "kind": name, "start": st, "end": en, "score": round(float(sc), 2),
                             "text": " ".join(s["text"] for s in segs if st <= s["start"] < en)[:1500]})
            print(f"  {out.name}  {st}-{en}s  score {sc:.2f}")
    mp = RAW / f"{vid}.manifest.json"
    mp.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return mp


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--kind", choices=["short", "video", "both"], default="both")
    ap.add_argument("--max", type=int, default=MAX_CLIPS_PER_SOURCE)
    a = ap.parse_args()
    process(a.url, a.kind, a.max)
