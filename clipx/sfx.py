"""Synthesised sound effects (numpy). Original sounds = no copyright, no downloads."""
import wave
import numpy as np

SR = 44100


def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1.0) * np.exp(-np.maximum(t - a, 0) / d)


def whoosh(length=0.55, seed=1):
    n = int(SR * length)
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n).astype(np.float32)
    y = np.zeros(n, dtype=np.float32)
    cut = np.linspace(0.015, 0.45, n) ** 1.2      # low-pass opening up = "whoosh"
    p = 0.0
    for i in range(n):
        p += cut[i] * (x[i] - p)
        y[i] = p
    t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 1.5
    y *= env
    return y / (np.abs(y).max() + 1e-6) * 0.8


def impact(length=0.7):
    n = int(SR * length)
    t = np.arange(n) / SR
    f = 38 + 110 * np.exp(-t * 14)                 # pitch drop
    ph = 2 * np.pi * np.cumsum(f) / SR
    boom = np.sin(ph) * np.exp(-t * 6)
    rng = np.random.default_rng(3)
    click = rng.standard_normal(n) * np.exp(-t * 90) * 0.5
    y = boom + click
    return (y / (np.abs(y).max() + 1e-6) * 0.95).astype(np.float32)


def glitch(length=0.28):
    n = int(SR * length)
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    y = np.zeros(n, dtype=np.float32)
    for k in range(5):
        s = int(rng.uniform(0, 0.8) * n)
        L = int(rng.uniform(0.012, 0.04) * SR)
        f = rng.choice([700, 1100, 1700, 2600])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * np.hanning(L)
        y[s:s + L] += seg[: n - s] * 0.5
    y += rng.standard_normal(n).astype(np.float32) * 0.08 * np.exp(-t * 10)
    return np.clip(y, -1, 1)


def pop(length=0.09):
    n = int(SR * length)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * (500 + 1800 * t) * t) * np.exp(-t * 45) * 0.8).astype(np.float32)


def riser(length=1.2):
    n = int(SR * length)
    t = np.arange(n) / SR
    f = 200 + 2800 * (t / length) ** 2
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / length) ** 1.5
    return (y * 0.5).astype(np.float32)


BANK = {"whoosh": whoosh, "impact": impact, "glitch": glitch, "pop": pop, "riser": riser}
_cache = {}


def mix(events, total, path, gain=0.55):
    """events: [(time_sec, name)]. Writes a mono 16-bit wav of length `total`."""
    out = np.zeros(int(SR * (total + 1)), dtype=np.float32)
    for t, name in events:
        if name not in _cache:
            _cache[name] = BANK[name]()
        s = _cache[name]
        i = int(t * SR)
        if i < 0 or i >= len(out):
            continue
        out[i:i + len(s)] += s[: len(out) - i]
    out = np.clip(out * gain, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    return path
