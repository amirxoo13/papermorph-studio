## فاز 6: بسته‌بندی کانتینر و اجرای Cloud Run Job با ۸ هسته (`pm-render-job`)

### ۱. چه ساختم
- `gcp/Dockerfile` و `services/render-job/Dockerfile` (27 خط — ایمیج `python:3.12.8-bookworm` مجهز به `ffmpeg`، مرورگرهای هدلس `chromium` و `firefox`، فونت‌های فارسی `Vazirmatn`، موتور فارسی و کتاب مستند `zahhak/ch01`)
- `gcp/render_only.sh` و `services/render-job/render_only.sh` (82 خط — اسکریپت اجرای ۵ مرحله‌ای درون کانتینر: بررسی پیش‌نیازها، اجرای `serve.py`، دروازهٔ `check.py`، رندر موازی با `export.py --jobs 8` و آپلود خروجی‌ها به باکت GCS)
- `gcp/cloudbuild.phase6.yaml` و `services/render-job/cloudbuild.phase6.yaml` (24 خط — پیکربندی بیلد ابری روی ماشین `E2_HIGHCPU_8` و انتشار ایمیج `us-central1-docker.pkg.dev/gen-lang-client-0484425781/papermorph/pm-render-job:phase6`)
- `reports/phase-6.md` (گزارش اثبات فاز ۶)

### ۲. دستور تست (عیناً)
```bash
gcloud builds submit services/render-job --config=services/render-job/cloudbuild.phase6.yaml --project=gen-lang-client-0484425781
gcloud run jobs update pm-render-job --image=us-central1-docker.pkg.dev/gen-lang-client-0484425781/papermorph/pm-render-job:phase6 --region=us-central1 --cpu=8 --memory=32Gi --task-timeout=21600s --max-retries=0 --project=gen-lang-client-0484425781
gcloud run jobs execute pm-render-job --region=us-central1 --project=gen-lang-client-0484425781 --update-env-vars="^:^RENDER_ONLY=1:BENCH_MODE=0:BOOK_SLUG=zahhak:CHAPTER=ch01:JOBS=8:EXPORT_EXTRA=--to mardas --height 540 --fps 20" --wait
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="pm-render-job" AND labels."run.googleapis.com/execution_name"="pm-render-job-q2dnw" AND NOT textPayload:"127.0.0.1 - -"' --limit=200 --format="value(textPayload)" --project=gen-lang-client-0484425781
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
BUILD_ID=07f50d11-1429-449f-bc86-6741077a0498 STATUS=SUCCESS DURATION=3M15S
IMAGE=us-central1-docker.pkg.dev/gen-lang-client-0484425781/papermorph/pm-render-job:phase6
------------------------------------------------------------
$ gcloud run jobs execute pm-render-job --region=us-central1 --project=gen-lang-client-0484425781 --update-env-vars="^:^RENDER_ONLY=1:BENCH_MODE=0:BOOK_SLUG=zahhak:CHAPTER=ch01:JOBS=8:EXPORT_EXTRA=--to mardas --height 540 --fps 20" --wait
Creating execution...
Provisioning resources..........................done
Starting execution.......................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................done
Running execution.........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................done
Done.
Execution [[1mpm-render-job-q2dnw[m] has successfully completed.

View details about this execution by running:
gcloud run jobs executions describe pm-render-job-q2dnw

Or visit https://console.cloud.google.com/run/jobs/executions/details/us-central1/pm-render-job-q2dnw?project=149479920662
[exit_status: 0]
------------------------------------------------------------
$ gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="pm-render-job" AND labels."run.googleapis.com/execution_name"="pm-render-job-q2dnw" AND NOT textPayload:"127.0.0.1 - -"' --limit=200 --format="value(textPayload)" --project=gen-lang-client-0484425781
=== [1/5] PRECONDITIONS ===
book=zahhak chapter=ch01 jobs=8 nproc=9
chapter html bytes: 14567
img files:   10
audio files: 21
=== [2/5] PREVIEW SERVER ===
serving site at http://localhost:8765/ (no-store, byte ranges)
server ready (PID=22)
=== [3/5] CHECK.PY (the engine's own gate) ===
== chromium ch01: 0 page errors, 0 console errors, 0 console warnings
== firefox ch01: 0 page errors, 0 console errors, 0 console warnings
== ch01 beat lengths: voice (pre + clip) and real (P.end), overrun past voice + 0.6 s hold
  open           voice  41.20  real  41.80   +0.00
  mardas         voice  29.66  real  30.26   +0.00
  pit            voice  35.45  real  36.05   +0.00
  cook           voice  34.49  real  35.09   +0.00
  kiss           voice  34.80  real  35.40   +0.00
  remedy         voice  33.55  real  34.15   +0.00
  jamshid        voice  33.34  real  33.94   +0.00
  cookrescue     voice  36.10  real  36.70   +0.00
  nightmare      voice  33.14  real  33.74   +0.00
  fereydun       voice  36.10  real  36.70   +0.00
  scroll         voice  32.98  real  33.58   +0.00
  kaveh          voice  34.54  real  35.14   +0.00
  tear           voice  32.83  real  33.43   +0.00
  banner         voice  34.44  real  35.04   +0.00
  damavand       voice  32.16  real  32.76   +0.00
  legacy         voice  34.22  real  34.82   +0.00
  film 558.59 s
=== [4/5] EXPORT ===
up to mardas: 2 beats
loudness -15.2 LUFS, -4.0 dBTP as the page mixes it; levelled to -16.0 LUFS, -4.8 dBTP (-0.8 dB, limiter at -1.8 dBFS; --lufs -16)
encoder libx264, 8 browsers
open: 836 frames
mardas: 605 frames
/tmp/export/ch01.mp4: -16.0 LUFS, -4.8 dBTP after the AAC encode
/tmp/export/ch01.mp4 (1.2 min, 1441 frames, 2 beats; sound peak 0.63) and ch01.srt
RENDER_WALL_SECONDS=41
total 11564
-rw-r--r-- 1 root root 11836021 Nov  9 17:26 ch01.mp4
-rw-r--r-- 1 root root     1912 Nov  9 17:26 ch01.srt
--- ffprobe ---
codec_name=h264
width=960
height=540
r_frame_rate=20/1
codec_name=aac
r_frame_rate=0/0
duration=72.052000
size=11836021
bit_rate=1314164
=== [5/5] UPLOAD ===
gs://gen-lang-client-0484425781-pm-published/renders/zahhak/ch01/ch01.mp4  (11836021 bytes)
gs://gen-lang-client-0484425781-pm-published/renders/zahhak/ch01/ch01.srt  (1912 bytes)
uploaded 2 files
Container called exit(0).
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
1. ساخت و انتشار ایمیج کانتینر در Artifact Registry بدون خطا: **پاس** (`BUILD_ID=07f50d11-1429-449f-bc86-6741077a0498` با وضعیت `SUCCESS`).
2. پیکربندی Cloud Run Job (`pm-render-job`) با `8 vCPU` و `32Gi` حافظه بدون GPU: **پاس** (`jobs=8`، اجرای ۸ مرورگر هم‌زمان `encoder libx264, 8 browsers`).
3. اجرای کامل ۵ مرحله درون کانتینر (`PRECONDITIONS` -> `PREVIEW SERVER` -> `CHECK.PY` -> `EXPORT` -> `UPLOAD`) با کد خروج صفر: **پاس** (اجرای `pm-render-job-q2dnw` با موفقیت کامل، پاس شدن `check.py` در Chromium و Firefox با صفر خطا، `RENDER_WALL_SECONDS=41` برای `72.052s` فیلم که `۲.۲۶` برابر سریع‌تر از `۹۲.۷۳` ثانیهٔ Colab است، و آپلود `ch01.mp4` و `ch01.srt` در `gs://gen-lang-client-0484425781-pm-published/renders/zahhak/ch01/`).

### ۶. چه چیزی کار نکرد یا تأیید نشد
هیچ.

### ۷. کامیت
- Branch: `main`
- Commit SHA: `216181ae885f4a7a9929252007c5591fce9c8ac2`
