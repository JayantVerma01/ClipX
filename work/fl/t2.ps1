$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX; $env:PYTHONPATH="D:\Jayant\ClipX"
$sw=[Diagnostics.Stopwatch]::StartNew()
python -W ignore -m clipx.pro work\fl\spec_test.json 2>&1 | Select -Last 8
"secs: " + [int]$sw.Elapsed.TotalSeconds
python work\fl\chk1.py output\pro_test.mp4
ffmpeg -y -v error -i output\pro_test.mp4 -vf "fps=2,scale=216:-1,tile=9x2" -frames:v 1 work\fl\pt.png
