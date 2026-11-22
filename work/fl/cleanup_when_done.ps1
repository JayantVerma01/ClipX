param([string]$Extra = "")
Set-Location D:\Jayant\ClipX
$env:PYTHONIOENCODING = "utf-8"
while ($true) {
  $busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'clipx\.factory work' }
  if (-not $busy) {
    python -W ignore work\fl\final_cleanup.py $Extra *>> factory\cleanup.out
    if ($LASTEXITCODE -eq 0) { break }
  }
  Start-Sleep 300
}
