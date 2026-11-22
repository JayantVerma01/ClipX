$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX; $env:PYTHONPATH="D:\Jayant\ClipX"
python -W ignore -c "import json; from clipx import pro2; d=pro2.render(json.load(open('work/fl/spec_test.json'))); print(d)" 2>&1 | Select -Last 4
Get-ChildItem other | Select Name
Test-Path output\pro_test.mp4
