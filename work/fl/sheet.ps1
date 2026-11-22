$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
foreach ($p in @(@("sPdTmBcXkas",30),@("Purk_N5WGfI",40))) {
  $f="work\$($p[0]).mp4"; $step=$p[1]
  $d=[double](ffprobe -v error -show_entries format=duration -of csv=p=0 $f)
  "$($p[0]) duration $([int]$d)s"
  ffmpeg -y -v error -i $f -vf "fps=1/$step,scale=240:-1,tile=9x8" -frames:v 1 "work\fl\sheet_$($p[0]).jpg"
}
