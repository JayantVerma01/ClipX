$env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
Set-Location D:\Jayant\ClipX
foreach ($id in "RmqkfQrqBdg","KVhMk5o3x8c") {
  python -m yt_dlp -q --no-warnings -f "bv*[height<=1080]+ba/b" --no-simulate --merge-output-format mp4 -o "work\ref\$id.%(ext)s" --print "$id | %(title)s | %(channel)s | %(duration)ss | %(view_count)s views | %(like_count)s likes | %(comment_count)s comments | %(upload_date)s" "https://www.youtube.com/shorts/$id" 2>&1 | Select -Last 2
  ffmpeg -y -v error -i "work\ref\$id.mp4" -vf "fps=3,scale=180:-1,tile=12x6" -frames:v 1 "work\fl\ref_$id.png"
}
