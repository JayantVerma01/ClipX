$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX; $env:PYTHONPATH="D:\Jayant\ClipX"
python -c "
import json
s={'slug':'t_cam_short','kind':'short','src':'work/6E2cBXFCDyQ.mp4','tag':'GTA 6','layout':'tall','title':['WEBCAM','AVOIDED'],'vcrop':0.8,'vy':0.1,
 'pieces':[{'s':513,'e':521,'cx':0.9,'zoom':'in'}],'caps':[{'p':0,'t':0.5,'d':2,'text':'NO FACECAM HERE'}],'flash':[],'sfx':[]}
json.dump(s,open('work/fl/t_cam_short.json','w'))
v=dict(s); v.update({'slug':'t_cam_video','kind':'video','title':['WEBCAM','BLURRED'],'pieces':[{'s':513,'e':521,'cx':0.5,'zoom':'none'}],'vcrop':1.0})
json.dump(v,open('work/fl/t_cam_video.json','w'))"
python -W ignore -m clipx.pro work\fl\t_cam_short.json 2>&1 | Select -Last 3
python -W ignore -m clipx.pro work\fl\t_cam_video.json 2>&1 | Select -Last 3
ffmpeg -y -v error -ss 2 -i output\pro_t_cam_short.mp4 -frames:v 1 -vf scale=360:-1 work\fl\tc1.png
ffmpeg -y -v error -ss 2 -i output\pro_t_cam_video.mp4 -frames:v 1 -vf scale=640:-1 work\fl\tc2.png
python -c "
from PIL import Image
a=Image.open('work/fl/tc1.png'); b=Image.open('work/fl/tc2.png')
im=Image.new('RGB',(a.width+b.width,max(a.height,b.height))); im.paste(a,(0,0)); im.paste(b,(a.width,0)); im.save('work/fl/tc.png')"
Get-Content other\meta\pro_t_cam_short.json | Select -First 12
