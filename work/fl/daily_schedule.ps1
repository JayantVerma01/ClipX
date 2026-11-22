# Runs when the PC starts: schedules the next Shorts on YouTube (2 a day, 11:00 and 17:00), up to 6 uploads a day.
# If there is no internet or the quota is used up it tries again every hour. Result lines: D:\Jayant\ClipX\factory\schedule.log
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
$env:PYTHONPATH = "D:\Jayant\ClipX"
$env:PYTHONIOENCODING = "utf-8"
$log = "D:\Jayant\ClipX\factory\schedule.log"
$me = $PID
$other = Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $me -and $_.Name -match 'powershell' -and $_.CommandLine -match 'daily_schedule\.ps1' }
if ($other) { exit }                      # one copy only
Start-Sleep 180                           # let the network come up
while ($true) {                           # keeps going while the PC stays on, so a new day is picked up without a restart
  $out = python -W ignore work\fl\sched_next.py auto 2>&1
  $code = $LASTEXITCODE
  $out | Where-Object { $_ -match 'SUMMARY|BLOCKED|upload stopped|scheduling|block-check failed|not touching' } | Add-Content -Path $log -Encoding utf8
  if ($code -eq 10) { Start-Sleep 3600 } else { Start-Sleep 14400 }   # uploads still owed: retry in 1 h; done: look again in 4 h
}
