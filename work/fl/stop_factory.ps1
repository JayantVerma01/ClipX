$me = $PID
Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $me -and $_.Name -match 'powershell' -and $_.CommandLine -match 'f_worker\.ps1|f_feed\.ps1|f_work[12]\.ps1' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'clipx\.factory' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-Process ffmpeg -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2
"running ffmpeg: " + (Get-Process ffmpeg -ErrorAction SilentlyContinue | Measure-Object).Count
