param([string]$Name = "w1")
$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
$env:PYTHONPATH="D:\Jayant\ClipX"
$env:PYTHONIOENCODING="utf-8"
python -u -W ignore -m clipx.factory feed *> "D:\Jayant\ClipX\factory\$Name.out"
