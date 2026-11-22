$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX; $env:PYTHONPATH="D:\Jayant\ClipX"
foreach ($s in "sens_nightclub","sens_vcafterdark") {
  "$(Get-Date -Format HH:mm:ss) start $s" | Out-File -Append -Encoding utf8 queue_sens2.log
  python -W ignore -m clipx.pro specs\$s.json 2>&1 | Select -Last 3 | Out-File -Append -Encoding utf8 queue_sens2.log
  python work\fl\chk1.py output\pro_$s.mp4 2>&1 | Out-File -Append -Encoding utf8 queue_sens2.log
}
python work\fl\thumbs_sens.py 2>&1 | Out-File -Append -Encoding utf8 queue_sens2.log
"ALL DONE" | Out-File -Append -Encoding utf8 queue_sens2.log
