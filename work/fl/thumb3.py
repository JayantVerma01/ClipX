import sys; sys.path.insert(0,'.')
from pathlib import Path
from clipx import thumb
O=Path('output')
thumb.make(O/'montage_vcdaynight_video.mp4','DAY TO NIGHT',O/'montage_vcdaynight_video_thumb.jpg'); print('ok')
