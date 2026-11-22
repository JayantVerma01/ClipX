$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX; $env:PYTHONPATH="D:\Jayant\ClipX"
$sw=[Diagnostics.Stopwatch]::StartNew()
python -W ignore -m clipx.montage work\sPdTmBcXkas.mp4 --kind short --dur 12 --tag "GTA 6" --hook "VICE CITY" --slug test --starts "90,450,1740" --labels "DAY|DUSK|NIGHT" 2>&1 | Select -Last 6
"secs: " + [int]$sw.Elapsed.TotalSeconds
python work\fl\chk1.py output\montage_test_short.mp4
