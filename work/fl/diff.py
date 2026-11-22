import subprocess, sys, numpy as np
def frames(path, ss, t, w=135, h=240):
    r = subprocess.run(["ffmpeg","-v","error","-ss",str(ss),"-t",str(t),"-i",path,"-vf",f"scale={w}:{h}","-f","rawvideo","-pix_fmt","gray","-"],capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)
    return a
path, ss, t = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
a = frames(path, ss, t)
d = np.abs(np.diff(a, axis=0)).mean(axis=(1,2))
print("frames", len(a), "median diff %.2f  p95 %.2f  max %.2f" % (np.median(d), np.percentile(d,95), d.max()))
# glitch = frame i differs from both neighbours but neighbours similar to each other
g = [(i+1, float(d[i]), float(d[i+1]), float(np.abs(a[i]-a[i+2]).mean())) for i in range(len(d)-1) if d[i] > 3*np.median(d)+2 and d[i+1] > 3*np.median(d)+2]
print("glitch frames (idx, d_in, d_out, d_skip):", g[:15], "count", len(g))
bright = a.mean(axis=(1,2)); print("brightness jumps >6:", [(i, round(float(bright[i+1]-bright[i]),1)) for i in range(len(bright)-1) if abs(bright[i+1]-bright[i])>6][:10])
