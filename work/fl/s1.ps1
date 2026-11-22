$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX; $env:PYTHONPATH="D:\Jayant\ClipX"
$sw=[Diagnostics.Stopwatch]::StartNew()
python -W ignore -m clipx.pro specs\beachbrawl.json 2>&1 | Select -Last 6
"secs: " + [int]$sw.Elapsed.TotalSeconds
python work\fl\chk1.py output\pro_beachbrawl.mp4
ffmpeg -y -v error -i output\pro_beachbrawl.mp4 -vf "fps=1/2.5,scale=216:-1,tile=10x2" -frames:v 1 work\fl\bb.png
