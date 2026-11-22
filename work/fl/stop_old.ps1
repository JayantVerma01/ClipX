$me = $PID
Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $me -and $_.Name -match 'powershell' -and $_.CommandLine -match 'queue_[sv]\.ps1' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'clipx\.pro|chk1\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-Process ffmpeg -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2
Set-Location D:\Jayant\ClipX
$done = "pro_chasecrash","pro_jettheft","pro_subwayshootout","pro_tankvspolice","pro_beachrampage","pro_v_beachrampage","pro_v_policechase","pro_v_tankvspolice"
Get-ChildItem other\prev\*.mp4 | ForEach-Object {
  if ($done -notcontains $_.BaseName) { Copy-Item $_.FullName "output\$($_.Name)" -Force }
}
Remove-Item other\prev -Recurse -Force
"output pro files: " + (Get-ChildItem output\pro_*.mp4).Count
"left running: " + (Get-Process ffmpeg -ErrorAction SilentlyContinue | Measure-Object).Count
