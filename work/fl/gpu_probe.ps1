$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
"== GPUs"
Get-CimInstance Win32_VideoController | ForEach-Object { "  " + $_.Name + " | driver " + $_.DriverVersion }
"== CPU"
Get-CimInstance Win32_Processor | ForEach-Object { "  " + $_.Name + " | cores " + $_.NumberOfCores + " threads " + $_.NumberOfLogicalProcessors + " | load " + $_.LoadPercentage + "%" }
"== ffmpeg hw encoders"
ffmpeg -hide_banner -encoders 2>$null | Select-String "h264_nvenc|h264_qsv|h264_amf|hevc_nvenc" | ForEach-Object { "  " + $_.Line.Trim() }
"== test encodes (5 s, 1080x1920)"
foreach ($enc in "h264_nvenc","h264_qsv","h264_amf") {
  $sw=[Diagnostics.Stopwatch]::StartNew()
  ffmpeg -y -v error -f lavfi -i "testsrc2=size=1080x1920:rate=30" -t 5 -c:v $enc -pix_fmt yuv420p "work\fl\gpu_$enc.mp4" 2>$null
  "  $enc exit=$LASTEXITCODE  " + [math]::Round($sw.Elapsed.TotalSeconds,1) + "s"
}
