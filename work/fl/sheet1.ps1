param([string]$Name)
$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
ffmpeg -y -v error -i "output\$Name.mp4" -vf "fps=1/4,scale=200:-1,tile=11x1" -frames:v 1 "work\fl\sheet_$Name.png"
