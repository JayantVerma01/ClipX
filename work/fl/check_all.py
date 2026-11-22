import subprocess, sys, glob, numpy as np
sys.path.insert(0, "work/fl")
def frames(path, ss, t, w=160, h=90):
    r = subprocess.run(["ffmpeg","-v","error","-ss",str(ss),"-t",str(t),"-i",path,"-vf",f"scale={w}:{h}","-f","rawvideo","-pix_fmt","gray","-"],capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)
for p in sorted(glob.glob("output/*_max.mp4")):
    dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p],capture_output=True,text=True).stdout)
    tot = bad = 0; per = []
    for ss in np.arange(0, dur - 5, 20):
        a = frames(p, ss, 20)
        if len(a) < 5: continue
        d = np.abs(np.diff(a, axis=0)).mean(axis=(1,2)); m = np.median(d)
        g = [i for i in range(len(d)-1) if d[i] > 3*m+2 and d[i+1] > 3*m+2 and np.abs(a[i]-a[i+2]).mean() < 0.6*min(d[i], d[i+1])]
        tot += len(a); bad += len(g); per += [round(ss + (i+1)/30, 1) for i in g]
    print(f"{p}: {dur:.0f}s, one-frame glitches: {bad}  at {per[:12]}")
