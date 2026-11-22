import sys; sys.path.insert(0,'.')
from pathlib import Path
from clipx import thumb
O=Path('output')
thumb.make(O/'sPdTmBcXkas_video01_raw.mp4','VICE CITY 4K',O/'sPdTmBcXkas_video01_max_thumb.jpg')
print('thumb ok')
