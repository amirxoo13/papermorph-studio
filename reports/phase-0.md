## فاز 0: محیط و مخزن

### ۱. چه ساختم
- `.gitignore` (9 خط)
- `reports/phase-0.md` (گزارش اثبات فاز ۰)

### ۲. دستور تست (عیناً)
```bash
nproc
free -g | head -2
ffmpeg -hide_banner -encoders | grep -i h264
uv --version
python3 -c "import playwright, sys; print(sys.version)"
gcloud config list --format=json
find vendor/Papermorph/.claude -type f | wc -l
git -C vendor/Papermorph rev-parse HEAD 2>/dev/null || git log -n 1 --format=%H -- vendor/Papermorph
cat .gitignore
wc -l .gitignore
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
$ nproc
4
[exit_status: 0]
--------------------------------------------------
$ free -g | head -2
               total        used        free      shared  buff/cache   available
Mem:              15           1          12           0           2          14
[exit_status: 0]
--------------------------------------------------
$ ffmpeg -hide_banner -encoders | grep -i h264
 V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
 V..... libx264rgb           libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 RGB (codec h264)
 V....D h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
 V..... h264_omx             OpenMAX IL H.264 video encoder (codec h264)
 V..... h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration) (codec h264)
 V..... h264_v4l2m2m         V4L2 mem2mem H.264 encoder wrapper (codec h264)
 V....D h264_vaapi           H.264/AVC (VAAPI) (codec h264)
 V..... nvenc                NVIDIA NVENC H.264 encoder (codec h264)
 V..... nvenc_h264           NVIDIA NVENC H.264 encoder (codec h264)
[exit_status: 0]
--------------------------------------------------
$ uv --version
uv 0.12.5 (x86_64-unknown-linux-gnu)
[exit_status: 0]
--------------------------------------------------
$ python3 -c "import playwright, sys; print(sys.version)"
3.13.15 (main, Aug  6 2026, 11:06:23) [GCC 11.4.0]
[exit_status: 0]
--------------------------------------------------
$ gcloud config list --format=json
{
  "component_manager": {
    "disable_update_check": "True"
  },
  "core": {
    "account": "kenneth65gray9269@gmail.com",
    "custom_ca_certs_file": "/etc/ssl/certs/ca-certificates.crt",
    "project": "gen-lang-client-0484425781",
    "universe_domain": "googleapis.com"
  }
}
[exit_status: 0]
--------------------------------------------------
$ find vendor/Papermorph/.claude -type f | wc -l
145
[exit_status: 0]
--------------------------------------------------
$ git -C vendor/Papermorph rev-parse HEAD 2>/dev/null || git log -n 1 --format=%H -- vendor/Papermorph
9628d3cfbc80b107e390be1bf50ef489a117dc9d
[exit_status: 0]
--------------------------------------------------
$ cat .gitignore
*.pdf
books/
books/*/pages/
content/
tools/
site/
out/
vendor/
__pycache__/
[exit_status: 0]
--------------------------------------------------
$ wc -l .gitignore
9 .gitignore
[exit_status: 0]
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
- `nproc`: پاس (`4` هسته، خط ۲ خروجی بالا)
- `free -g | head -2`: پاس (`Mem: 15 total, 14 available`، خطوط ۵ تا ۶ خروجی بالا)
- `ffmpeg -hide_banner -encoders | grep -i h264`: پاس (`libx264` موجود است، خط ۹ خروجی بالا)
- `uv --version`: پاس (`uv 0.12.5`، خط ۲۰ خروجی بالا)
- `python3 -c "import playwright, sys; print(sys.version)"`: پاس (`3.13.15`، خط ۲۴ خروجی بالا)
- `gcloud config list --format=json`: پاس (پروژه `gen-lang-client-0484425781`، خطوط ۲۸ تا ۳۹ خروجی بالا)
- تعداد فایل‌های اسکیل (`find vendor/Papermorph/.claude -type f | wc -l`): پاس (خط ۴۳ خروجی بالا)
- کامیت فعلی `vendor/Papermorph`: پاس (خط ۴۷ خروجی بالا)
- `.gitignore` شامل `*.pdf`, `books/*/pages/`, `books/`, `content/`, `tools/`, `site/`, `out/`: پاس (خطوط ۵۱ تا ۵۷ خروجی بالا)

### ۶. چه چیزی کار نکرد یا تأیید نشد
هیچ.

### ۷. کامیت
- Branch: `main`
- Commit SHA: `cc7cb692f29f2e061bb05692f60ac49ffcf2c7b4`
