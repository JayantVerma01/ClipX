import subprocess
from PIL import Image
subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "24", "-i", "output/pro_sens_nightclub.mp4", "-vf", "fps=1.2,scale=160:-1,tile=7x1",
                "-frames:v", "1", "work/fl/nc_end.png"])
a = Image.open("other/thumbs/pro_sens_nightclub_thumb.jpg").resize((640, 360))
b = Image.open("work/fl/nc_end.png")
b = b.resize((640, int(b.height * 640 / b.width)))
im = Image.new("RGB", (1280, max(360, b.height)))
im.paste(a, (0, 0))
im.paste(b, (640, 0))
im.save("work/fl/nc_check.png")
print("ok")
