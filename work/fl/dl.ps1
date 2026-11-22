$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
python -u -W ignore work\fl\dl2.py *>&1 | Out-File -Encoding utf8 work\fl\dl2.log
