$b = "-NoProfile","-ExecutionPolicy","Bypass","-File"
Start-Process -WindowStyle Hidden powershell -ArgumentList ($b + "D:\Jayant\ClipX\work\fl\f_feeder.ps1","-Name","feed")
Start-Process -WindowStyle Hidden powershell -ArgumentList ($b + "D:\Jayant\ClipX\work\fl\f_worker.ps1","-Name","w1")
Start-Sleep 3
Start-Process -WindowStyle Hidden powershell -ArgumentList ($b + "D:\Jayant\ClipX\work\fl\f_worker.ps1","-Name","w2")
Start-Sleep 3
Start-Process -WindowStyle Hidden powershell -ArgumentList ($b + "D:\Jayant\ClipX\work\fl\f_worker.ps1","-Name","w3")
"started feeder + w1 w2 w3 (shorts first)"
