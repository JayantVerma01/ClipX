"python factory procs:"
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'clipx\.factory' } | ForEach-Object { "  " + $_.ProcessId + " " + ($_.CommandLine -replace '.*clipx\.factory','factory') + " started " + $_.CreationDate.ToString('HH:mm') }
"ffmpeg procs:"
Get-Process ffmpeg -ErrorAction SilentlyContinue | ForEach-Object { "  " + $_.Id + " cpu " + [int]$_.CPU + "s started " + $_.StartTime.ToString('HH:mm') }
"cpu load %: " + (Get-CimInstance Win32_Processor).LoadPercentage
"last boot: " + (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('MM-dd HH:mm')
