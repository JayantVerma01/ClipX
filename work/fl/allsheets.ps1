$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
$pk = @{ "8-DRGbQ1IXc"="497,403,221,371,75,185"; "9TLwyuGDSmI"="143,561,193,335,475,118"; "-UuHA1h-Cf8"="340,379,560,513,466,21";
 "6E2cBXFCDyQ"="351,515,418,29,153,382"; "BgO-5PVOj5c"="305,158,186,239,6,79"; "bfY0coYanSg"="150,284,117,341,67,3";
 "OnWC__OxyTk"="179,135,219,45,110,9"; "ORYwlJXszi4"="173,75,112,312,282,338" }
foreach ($k in $pk.Keys) { python work\fl\winsheet.py $k $pk[$k] 2.5 }
"ALL SHEETS"
