Set-Location D:\Jayant\ClipX
$env:PYTHONIOENCODING = 'utf-8'
while (-not (Test-Path factory\FEED_DONE)) { Start-Sleep 60 }
python work\fl\add_local.py refeed *> factory\refeed.out
python -u -W ignore -m clipx.factory feed *> factory\feed2.out
