import subprocess, sys, json, numpy as np
from pathlib import Path
def run(vid, n=8, win=6.0, sep=25.0):
    p = f"work/{vid}.mp4"
    # audio energy per 0.5s
    raw = subprocess.run(["ffmpeg","-v","error","-i",p,"-vn","-ac","1","-ar","8000","-f","s16le","-"],capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32)/32768
    h = 4000; m = len(a)//h; e = np.sqrt((a[:m*h].reshape(m,h)**2).mean(1))
    # motion per 0.5s via 2fps gray frames
    fr = subprocess.run(["ffmpeg","-v","error","-i",p,"-vf","fps=2,scale=96:54","-f","rawvideo","-pix_fmt","gray","-"],capture_output=True).stdout
    f = np.frombuffer(fr, np.uint8).reshape(-1,54,96).astype(np.float32)
    mo = np.abs(np.diff(f,axis=0)).mean((1,2)); mo = np.append(mo, mo[-1])
    L = min(len(e), len(mo)); e, mo = e[:L], mo[:L]
    z = lambda x: (x - x.mean())/(x.std()+1e-6)
    s = z(e) + z(np.clip(mo, 0, np.percentile(mo, 98)))
    k = int(win*2); sc = np.convolve(s, np.ones(k)/k, mode="valid")
    out, used = [], []
    for i in np.argsort(-sc):
        t = i/2
        if all(abs(t-u) >= sep for u in used) and t > 5:
            out.append((round(t,1), round(float(sc[i]),2))); used.append(t)
        if len(out) >= n: break
    return out
if __name__ == "__main__":
    res = {}
    for vid in sys.argv[1:]:
        res[vid] = run(vid); print(vid, res[vid], flush=True)
    json.dump(res, open("work/fl/peaks_%s.json" % sys.argv[1], "w"))
