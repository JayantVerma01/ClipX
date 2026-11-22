"""Find the best non-overlapping windows. Pure local heuristics: 0 LLM tokens."""
import re
import numpy as np
from .config import HYPE_WORDS


def _smooth(x, k=3):
    return np.convolve(x, np.ones(k) / k, mode="same")


def find_moments(segments, energy, kind, max_clips, external=None, ext_weight=0.9):
    lo, hi = kind
    dur = len(energy)
    if dur < lo:
        return []
    # per-second features
    e = (energy - energy.mean()) / (energy.std() + 1e-6)
    wps = np.zeros(dur)
    hype = np.zeros(dur)
    for s in segments:
        for w in s["words"]:
            t = int(w["s"])
            if t >= dur:
                continue
            wps[t] += 1
            token = re.sub(r"\W", "", w["w"].lower())
            if token in HYPE_WORDS:
                hype[t] += 1
            if "!" in w["w"] or "?" in w["w"]:
                hype[t] += 0.5
    score = _smooth(np.clip(e, -1, 4)) + 0.25 * _smooth(wps) + 1.0 * _smooth(hype, 5)
    if external is not None and len(external) >= 1:        # chat replay / most-replayed signal (clipx.signals), 0..4
        ext = np.zeros(dur)
        ext[: min(dur, len(external))] = np.asarray(external[:dur], dtype=float)
        score = score + ext_weight * _smooth(ext, 5)
    cs = np.concatenate([[0], np.cumsum(score)])

    # candidate window ends/starts snap to speech segment boundaries
    starts = sorted({int(s["start"]) for s in segments} | {0})
    ends = sorted({int(s["end"]) + 1 for s in segments})
    target = (lo + hi) / 2
    cands = []
    for st in starts:
        # best end near target length within [lo, hi]
        e_opts = [x for x in ends if lo <= x - st <= hi and x <= dur]
        if not e_opts:
            continue
        en = min(e_opts, key=lambda x: abs((x - st) - target))
        mean = (cs[en] - cs[st]) / (en - st)
        # reward a strong opening (hook) in the first 5 seconds
        hook = score[st: st + 5].mean()
        cands.append((mean + 0.3 * hook, st, en))
    cands.sort(reverse=True)

    chosen = []
    for sc, st, en in cands:
        if all(en <= a or st >= b for _, a, b in chosen):
            chosen.append((sc, st, en))
        if len(chosen) >= max_clips:
            break
    return sorted(chosen, key=lambda c: c[1])
