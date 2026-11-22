$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
foreach ($s in "sens_dancefloor","sens_firstnight","sens_nightclub","sens_yacht") {
  ffmpeg -y -v error -i output\pro_$s.mp4 -vf "fps=1/2.2,scale=200:-1,tile=10x2" -frames:v 1 work\fl\rv_$s.png
}
ffmpeg -y -v error -i output\pro_sens_vcafterdark.mp4 -vf "fps=1/6,scale=320:-1,tile=5x6" -frames:v 1 work\fl\rv_sens_video.png
python -c "
from PIL import Image
import glob
fs=sorted(glob.glob('other/thumbs/pro_sens_*_thumb.jpg'))
im=Image.new('RGB',(3*427,2*240),'black')
for i,f in enumerate(fs):
    t=Image.open(f).resize((427,240)); im.paste(t,((i%3)*427,(i//3)*240))
im.save('work/fl/thumbs_sens_sheet.png'); print(fs)"
