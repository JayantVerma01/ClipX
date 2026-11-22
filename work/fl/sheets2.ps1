$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
foreach ($id in "ID-C0E_DidA","1lrxJBis9OE","3i_MjxVTAbQ","iBysITGTVeI","RSy0UkR0JBs","boNEXq35Hg0") {
  while (-not (Test-Path "work\$id.meta.json")) { Start-Sleep 5 }
  $d=[double](ffprobe -v error -show_entries format=duration -of csv=p=0 "work\$id.mp4")
  $step=[math]::Max(4,[math]::Ceiling($d/60))
  "$id dur=$([int]$d) step=$step"
  ffmpeg -y -v error -i "work\$id.mp4" -vf "fps=1/$step,scale=192:-1,tile=10x6" -frames:v 1 "work\fl\sx_$id.png"
}
"SHEETS DONE"
