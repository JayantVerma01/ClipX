$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
foreach ($s in "chasecrash","jettheft","subwayshootout","tankvspolice") {
  ffmpeg -y -v error -i output\pro_$s.mp4 -vf "fps=1/2.5,scale=200:-1,tile=10x2" -frames:v 1 work\fl\rv_$s.png
}
foreach ($s in "v_beachrampage","v_policechase") {
  ffmpeg -y -v error -i output\pro_$s.mp4 -vf "fps=1/8,scale=320:-1,tile=4x4" -frames:v 1 work\fl\rv_$s.png
}
"ok"
