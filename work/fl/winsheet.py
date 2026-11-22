import subprocess, sys, io
from PIL import Image, ImageDraw
vid = sys.argv[1]; ts = [float(x) for x in sys.argv[2].split(",")]; step = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
cols = 5; w, h = 256, 144
im = Image.new("RGB", (cols*w, len(ts)*h), "black"); d = ImageDraw.Draw(im)
for r, t in enumerate(ts):
    for c in range(cols):
        tt = t + c*step
        b = subprocess.run(["ffmpeg","-v","error","-ss",f"{tt:.2f}","-i",f"work/{vid}.mp4","-frames:v","1","-vf",f"scale={w}:{h}","-f","image2pipe","-vcodec","png","-"],capture_output=True).stdout
        try: im.paste(Image.open(io.BytesIO(b)), (c*w, r*h))
        except Exception: pass
        d.text((c*w+4, r*h+4), f"{tt:.0f}s", fill="yellow")
im.save(f"work/fl/ws_{vid}.png"); print("saved")
