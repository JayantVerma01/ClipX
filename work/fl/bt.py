import sys, time; sys.path.insert(0,'.')
from clipx import bars
t=time.time(); print(bars.detect("work/sPdTmBcXkas.mp4",3840,2160), round(time.time()-t,1),"s")
