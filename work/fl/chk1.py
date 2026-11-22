import subprocess,sys,numpy as np
p=sys.argv[1]
dur=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p],capture_output=True,text=True).stdout)
bad=[]
for ss in np.arange(0,dur-5,30):
    r=subprocess.run(["ffmpeg","-v","error","-ss",str(ss),"-t","30","-i",p,"-vf","scale=160:90","-f","rawvideo","-pix_fmt","gray","-"],capture_output=True)
    a=np.frombuffer(r.stdout,np.uint8).reshape(-1,90,160).astype(np.float32)
    d=np.abs(np.diff(a,axis=0)).mean(axis=(1,2));m=np.median(d)
    bad+=[round(ss+(i+1)/30,1) for i in range(len(d)-1) if d[i]>3*m+2 and d[i+1]>3*m+2 and np.abs(a[i]-a[i+2]).mean()<0.6*min(d[i],d[i+1])]
print(p,round(dur),"s one-frame glitches:",len(bad),bad[:10])
