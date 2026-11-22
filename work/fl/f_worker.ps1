param([string]$Name = "w1", [string]$Prefer = "")
$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
$env:PYTHONPATH="D:\Jayant\ClipX"
$env:PYTHONIOENCODING="utf-8"
if ($Prefer) { $env:CLIPX_PREFER = $Prefer }
python -u -W ignore -m clipx.factory work *> "D:\Jayant\ClipX\factory\$Name.out"
