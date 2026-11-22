$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX; $env:PYTHONPATH="D:\Jayant\ClipX"
foreach ($s in "chasecrash","jettheft","subwayshootout","tankvspolice","beachrampage","nightfight","cruiseship","sixstars","trafficchaos") {
  "$(Get-Date -Format HH:mm:ss) start $s" | Out-File -Append -Encoding utf8 queue_s.log
  python -W ignore -m clipx.pro specs\$s.json 2>&1 | Select -Last 3 | Out-File -Append -Encoding utf8 queue_s.log
  python work\fl\chk1.py output\pro_$s.mp4 2>&1 | Out-File -Append -Encoding utf8 queue_s.log
}
"ALL DONE" | Out-File -Append -Encoding utf8 queue_s.log
