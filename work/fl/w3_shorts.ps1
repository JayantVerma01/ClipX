$ps = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'powershell' -and $_.CommandLine -match 'f_worker\.ps1' -and $_.CommandLine -match 'w3' }
foreach ($p in $ps) {
  $py = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $p.ProcessId }
  foreach ($c in $py) {
    Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $c.ProcessId } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Stop-Process -Id $c.ProcessId -Force -ErrorAction SilentlyContinue
  }
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep 3
Get-ChildItem D:\Jayant\ClipX\factory\lock | Where-Object { $_.Name -match '_v\d+$' } | ForEach-Object {
  $slug = $_.Name
  Remove-Item $_.FullName -Force
  $half = "D:\Jayant\ClipX\output\$slug.mp4"
  if (Test-Path $half) { Remove-Item $half -Force }
  "released $slug"
}
Start-Process -WindowStyle Hidden powershell -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","D:\Jayant\ClipX\work\fl\f_worker.ps1","-Name","w3"
Start-Sleep 20
Get-ChildItem D:\Jayant\ClipX\factory\lock | Select-Object -ExpandProperty Name
