p = "clipx/pro.py"
s = open(p, encoding="utf-8").read()
BS = chr(92) * 2

# imports
s = s.replace("from . import sfx\n", "from . import sfx, framing\nimport datetime\n", 1)

# (a) per-piece crop position with automatic webcam avoidance
old = '        cx = p.get("cx", 0.5)\n        if short and sq:'
new = '''        cx = p.get("cx", 0.5)
        cx = 0.5 if cx == "auto" else cx
        cam, blur = None, ""
        sw, sh = probe(_src(p))
        if spec.get("facecam", True):
            try:
                cam, _, _ = framing.facecam(_src(p), p["s"], p["e"])
            except Exception:
                cam = None
        if cam is not None and short:
            vc_ = spec.get("vcrop", 0.80)
            cw_px = sh * vc_ * (asp if sq else 9 / 16)
            cx, clear = framing.crop_cx_avoiding(cam, sw, sh, cw_px, preferred=cx)
            notes.append(f"piece {k}: streamer webcam detected at {tuple(round(v) for v in cam)}; crop moved to cx={cx:.2f}"
                         + ("" if clear else " (could not fully clear it)"))
        elif cam is not None:
            x0, y0, x1, y1 = [int(v) for v in cam]
            blur = (f"split=2[pa{k}][pb{k}];[pb{k}]crop={x1 - x0}:{y1 - y0}:{x0}:{y0},boxblur=24:6[pc{k}];"
                    f"[pa{k}][pc{k}]overlay={x0}:{y0}[pm{k}];[pm{k}]")
            notes.append(f"piece {k}: streamer webcam detected at {(x0, y0, x1, y1)}; blurred")
        if short and sq:'''
assert old in s
s = s.replace(old, new, 1)

old = '''        g.append(f"[{k}:v]{sp_f}fps=30,{crop},scale={big_w}:{big_h}:flags=lanczos,"'''
new = '''        head = f"[{k}:v]{sp_f}fps=30," + blur
        g.append(f"{head}{crop},scale={big_w}:{big_h}:flags=lanczos,"'''
assert old in s
s = s.replace(old, new, 1)
# the notes list must exist before the loop
s = s.replace("    for p in pcs:\n        cmd += [\"-ss\"", "    notes = []\n    for p in pcs:\n        cmd += [\"-ss\"", 1)

# (b) credit overlay: auto from work/<id>.meta.json
old = '    slug = spec["slug"]\n    ass = AUX'
new = '''    # on-screen credit to the footage's creator (like GTA-Auto-Clipper's "via ..." line) - credit is courtesy, not permission
    sources = {}
    for p_ in pcs:
        sp_ = _src(p_)
        sources.setdefault(sp_.stem, []).append([p_["s"], p_["e"]])
    meta_of = {}
    for vid_ in sources:
        mf = ROOT / "work" / f"{vid_}.meta.json"
        if mf.exists():
            try:
                meta_of[vid_] = json.loads(mf.read_text(encoding="utf-8-sig"))
            except ValueError:
                pass
    names = []
    for vid_ in sources:
        nm = (meta_of.get(vid_) or {}).get("channel")
        if nm and nm not in names:
            names.append(nm)
    credit = spec.get("credit", " + ".join(names[:2]) if names else None)
    if credit:
        cr = f"via {credit}"
        if short:
            extra.append(f"Dialogue: 5,{_ts(0.4)},{_ts(min(dur, 5.0))},Hook,,0,0,0,,{{''' + BS + 'an8' + BS + 'pos(540,1668)' + BS + 'fs32' + BS + 'bord4' + BS + '1c&HFFFFFF&' + BS + '3c&H000000&' + BS + '''fad(200,300)}}{cr}")
        else:
            extra.append(f"Dialogue: 5,{_ts(0.4)},{_ts(min(dur, 5.0))},Hook,,0,0,0,,{{''' + BS + 'an3' + BS + 'pos(1880,1040)' + BS + 'fs30' + BS + 'bord4' + BS + '1c&HFFFFFF&' + BS + '3c&H000000&' + BS + '''fad(200,300)}}{cr}")
    slug = spec["slug"]
    ass = AUX'''
assert old in s
s = s.replace(old, new, 1)

# (c) provenance sidecar after rendering
old = '    subprocess.run(cmd, check=True, cwd=AUX)\n    return dst, dur'
new = '''    subprocess.run(cmd, check=True, cwd=AUX)
    meta_dir = AUX / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / f"pro_{slug}.json").write_text(json.dumps({
        "file": dst.name, "kind": spec.get("kind"), "seconds": round(dur, 2),
        "rendered_at": datetime.datetime.now().isoformat(timespec="seconds"), "credit": credit,
        "sources": [{"id": v, "url": (meta_of.get(v) or {}).get("url") or f"https://www.youtube.com/watch?v={v}",
                     "channel": (meta_of.get(v) or {}).get("channel"), "title": (meta_of.get(v) or {}).get("title"),
                     "license": (meta_of.get(v) or {}).get("license"), "ranges": r} for v, r in sources.items()],
        "framing_notes": notes, "spec": spec}, indent=1, ensure_ascii=False), encoding="utf-8")
    return dst, dur'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("patched")
