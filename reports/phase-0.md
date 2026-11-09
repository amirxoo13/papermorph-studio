## فاز 0: محیط و مخزن

### ۱. چه ساختم
- `.gitignore` (9 خط)
- `reports/phase-0.md` (93 خط)
- ساختار پوشه‌های مخزن (`gcp/.gitkeep`، `specs/.gitkeep`، `reports/.gitkeep`، `infra/.gitkeep` و کلون دست‌نخوردهٔ `vendor/Papermorph`)

### ۲. دستور تست (عیناً)
```bash
nproc
free -g | head -2
ffmpeg -hide_banner -encoders | grep -i h264
uv --version
python3 -c "import playwright, sys; print(sys.version)"
gcloud config list --format=json
find vendor/Papermorph/.claude -type f | wc -l
git -C vendor/Papermorph rev-parse HEAD
git remote -v
cat .gitignore
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
>>> $ nproc
4
>>> $ free -g | head -2
               total        used        free      shared  buff/cache   available
Mem:              15           0          10           0           3          14
>>> $ ffmpeg -hide_banner -encoders | grep -i h264
 V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
 V..... libx264rgb           libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 RGB (codec h264)
 V....D h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
 V..... h264_omx             OpenMAX IL H.264 video encoder (codec h264)
 V..... h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration) (codec h264)
 V..... h264_v4l2m2m         V4L2 mem2mem H.264 encoder wrapper (codec h264)
 V....D h264_vaapi           H.264/AVC (VAAPI) (codec h264)
 V..... nvenc                NVIDIA NVENC H.264 encoder (codec h264)
 V..... nvenc_h264           NVIDIA NVENC H.264 encoder (codec h264)
>>> $ uv --version
uv 0.12.5 (x86_64-unknown-linux-gnu)
>>> $ python3 -c "import playwright, sys; print(sys.version)"
3.13.15 (main, Aug  6 2026, 11:06:23) [GCC 11.4.0]
>>> $ gcloud config list --format=json
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
>>> $ find vendor/Papermorph/.claude -type f | wc -l
142
>>> $ git -C vendor/Papermorph rev-parse HEAD
9628d3cfbc80b107e390be1bf50ef489a117dc9d
>>> $ git remote -v
origin	https://github.com/amirxoo13/papermorph-studio.git (fetch)
origin	https://github.com/amirxoo13/papermorph-studio.git (push)
>>> $ cat .gitignore
*.pdf
books/
books/*/pages/
content/
tools/
site/
out/
vendor/
__pycache__/
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
- `nproc`: **پاس** (خط ۲ خروجی: `4`)
- `free -g | head -2`: **پاس** (خط ۴ و ۵ خروجی: `Mem: 15 total, 14 available`)
- `ffmpeg -hide_banner -encoders | grep -i h264`: **پاس** (خط ۷ تا ۱۵ خروجی: حضور `libx264` و سایر انکدرهای H.264)
- `uv --version`: **پاس** (خط ۱۷ خروجی: `uv 0.12.5 (x86_64-unknown-linux-gnu)`)
- `python3 -c "import playwright, sys; print(sys.version)"`: **پاس** (خط ۱۹ و ۲۰ خروجی: ایمپورت بدون خطای `playwright` و چاپ نسخهٔ پایتون `3.13.15`)
- `gcloud config list --format=json`: **پاس** (خط ۲۲ تا ۳۲ خروجی: پروژهٔ `gen-lang-client-0484425781` و اکانت فعال)
- تعداد فایل‌های اسکیل (`find vendor/Papermorph/.claude -type f | wc -l`): **پاس** (خط ۳۴ خروجی: `142`)
- کامیت فعلی Papermorph (`git -C vendor/Papermorph rev-parse HEAD`): **پاس** (خط ۳۶ خروجی: `9628d3cfbc80b107e390be1bf50ef489a117dc9d`)
- عدم وجود توکن در `git remote -v`: **پاس** (خط ۳۸ و ۳۹ خروجی: آدرس تمیز `https://github.com/amirxoo13/papermorph-studio.git`)
- فایل `.gitignore` شامل `*.pdf`، `books/`، `content/`، `tools/`، `site/`، `out/`: **پاس** (خط ۴۱ تا ۵۰ خروجی)

### ۶. چه چیزی کار نکرد یا تأیید نشد
هیچ.

### ۷. کامیت
شاخه: `main` — کامیت کد فاز ۰: `1de924923e1d9e7548f9084c4c4566c84e19bfd0`
