param([string]$At = "19:30")
$t = [datetime]::ParseExact($At, "HH:mm", $null)
if ($t -lt (Get-Date)) { $t = $t.AddDays(1) }
Start-Sleep -Seconds ([int]($t - (Get-Date)).TotalSeconds)
Set-Location D:\Jayant\ClipX
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Jayant\ClipX\work\fl\stop_factory.ps1 *> D:\Jayant\ClipX\factory\stop_at.out
$env:PYTHONIOENCODING = "utf-8"
python -W ignore -m clipx.factory unlock *>> D:\Jayant\ClipX\factory\stop_at.out
"stopped at $(Get-Date -Format HH:mm:ss)" >> D:\Jayant\ClipX\factory\stop_at.out
