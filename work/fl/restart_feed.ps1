$feed = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'clipx\.factory feed' }
foreach ($f in $feed) {
  Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $f.ProcessId } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Stop-Process -Id $f.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep 2
Set-Location D:\Jayant\ClipX
python -c "import json; p='factory/fed.json'; s=json.load(open(p,encoding='utf-8')); s['done'].append('sPdTmBcXkas'); json.dump(s,open(p,'w',encoding='utf-8')); print('skipped 4K source; done =',len(s['done']))"
Start-Process -WindowStyle Hidden powershell -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","D:\Jayant\ClipX\work\fl\f_feeder.ps1","-Name","feed"
"feeder restarted"
