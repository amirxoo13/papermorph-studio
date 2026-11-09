## فاز 2: بنچمارک رندر (آماده‌سازی کد و سنجهٔ سنجش + اجرای کوتاه سلامت زنجیره در Colab)

### ۱. چه ساختم
- `gcp/bench_render.py` (142 خط)
- `reports/phase-2.md` (گزارش اثبات فاز ۲)

### ۲. دستور تست (عیناً)
```bash
uv run --with playwright --with numpy vendor/Papermorph/.claude/skills/papermorph/scripts/export.py --help
python3 gcp/bench_render.py --to bosch --jobs 2,4
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
$ uv run --with playwright --with numpy vendor/Papermorph/.claude/skills/papermorph/scripts/export.py --help
usage: export.py [-h] [--url URL] [--out OUT] [--fps FPS] [--jobs JOBS]
                 [--height HEIGHT] [--link LINK] [--query QUERY] [--lufs LUFS]
                 [--to BEAT] [--no-tags] [--captions] [--stems] [--timeout S]
                 chapter

Export a chapter (a lesson, a picture-book episode, a documentary or a short) as an MP4 video with an .srt caption file, for video sites.

    uv run --with playwright --with numpy export.py ch12 --url http://localhost:8765/<book>/ --out OUT
    ... --fps 30 --height 1080 --link https://example.org/<book>/ch12/   # a lesson: its address on the end card
    ... --lufs -14 (the sound's loudness; default -16, off: as mixed) --to scene1 (stop after that beat)

The engine draws every frame as a pure function of the beat time, so frames are rendered by seeking, not by
recording playback: the video is exact and the same on every run. The sound is mixed the way the page plays it:
each beat's clip from its `pre` on, and in a film (a picture book or a documentary) the sfx() effects (cut at the end
of their scene, as a scene change stops them; a bed, { loop: true }, laid again and again to its `to` or the beat's end) and the BGM tracks with their crossfades, ducking and MUSIC_OFF. Question beats (quick
checks and practice) are left out, and then the video ends on a card saying they are in the interactive lesson
(--link adds its address; such a lesson plays no music() on the page, so none in the video either); in a film with interactive moments (CHAPTER.film, e.g. the reader fires a rifle) they stay in,
each holding its picture for its `hold` seconds (1.5 by default; the scene's breathing and blinking go on and its beds
play, the music up at 70 %, as the page plays it while it waits) before the next beat plays as if the reader had acted. A beat with `video: false` in its fourth slot is left
out, and `video: S` ends it S seconds into its clock, sound and captions cut there, with no wait: a game that only
works on the page (a listen-and-find stop, findWords) stays out of the video. With --link and no question beats left
out (a picture book or a film, which otherwise ends on its own last scene), it adds a 4 s card with the title and
the link only: leave --link off a film.

Loudness: the mix is levelled to --lufs integrated (default -16, a level video sites and phones play without turning
it up much; YouTube plays louder ones at -14) with its true peak under -1.5 dBTP, by a gain and a limiter as level.py
levels a clip; the run prints the loudness before and after, and of the finished MP4. --lufs off keeps the mix as the
page plays it (a picture book's comes out near -19), turned down as a whole only if it would clip.

The sound comes from the engine's own lists (sfx(), music(), MUSIC_OFF and MUSIC_UP_IN_PRE as window properties). A
page that declares its own SFX, BGM, sfx(), music() or MUSIC_OFF (an older book's sound player) hides them from the
engine: the run names each such global and says that sound is not in the video.
Odd sizes (an upright --height 720 is 405 wide) are cut to even ones, as H.264 needs. The video is written to
OUT/chNN.tmp.mp4 and renamed when done, so a failed run leaves an earlier OUT/chNN.mp4 alone. Captions go out as
OUT/chNN.srt to upload with the video; --captions also burns them in, as the page draws them with captions on (its own
font, box and place, a foreign line's subtitle too), with no ffmpeg subtitle filter, which many ffmpeg builds lack
(Homebrew's ffmpeg 9 has neither subtitles nor drawtext). --stems also writes OUT/chNN.voice.wav, .effects.wav and
.music.wav, each as the page plays it before the mix is levelled: a bed or an effect measured against the voice. Needs ffmpeg; serve the site over HTTP first (a wrong port or book path stops
the run with a plain message). A page load, script or screenshot that takes over --timeout seconds (default 120; a busy
machine draws slowly) stops the run with a message naming the pass, beat and frame it was on, and exit status 1.

An upright film (a short) goes out with its source and AI-illustration tags (the page's ?tags query), since a video
leaves the page that credits them; --no-tags leaves them out. A landscape chapter shows them only with --query tags.

Speed: frames are shot by --jobs browsers at once (default: half the CPU threads, at most 8), frame f by browser
f % jobs, and written in order. The browsers ask for the GPU (Chromium falls back to software where there is none),
and the video goes to the first hardware H.264 encoder that works on this machine (NVENC, Quick Sync, AMF,
VideoToolbox), else libx264; the run prints which.

positional arguments:
  chapter          chapter folder under --url, e.g. ch12

options:
  -h, --help       show this help message and exit
  --url URL        the book served over HTTP, ending in /
  --out OUT        output folder
  --fps FPS
  --jobs JOBS      browsers shooting frames at once (default: half the CPU
                   threads, at most 8)
  --height HEIGHT  video height (default 1080 landscape, 1920 portrait)
  --link LINK      address of the interactive lesson, shown on the end card
  --query QUERY    extra page query, e.g. tags (the source and AI-illustration
                   tags)
  --lufs LUFS      integrated loudness of the video's sound (default -16; off:
                   as the page mixes it)
  --to BEAT        stop after this beat (its id): a first part of the film,
                   e.g. one scene to check
  --no-tags        an upright film without its source and AI tags (shown by
                   default)
  --captions       burn the page's own captions into the frames (the .srt is
                   written too)
  --stems          also write the voice, effects and music stems as WAV, at
                   the page's levels
  --timeout S      seconds a page load, script or screenshot may take before
                   the run stops (default 120)
[exit_status: 0]
--------------------------------------------------
$ python3 gcp/bench_render.py --to bosch --jobs 2,4
nproc=4
ffmpeg_version=ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021 the FFmpeg developers
CHROME=/root/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome
chromium-ok
server:200
============================================================
RUN jobs=2 to_beat=bosch
$ time -p uv run --with playwright --with numpy vendor/Papermorph/.claude/skills/papermorph/scripts/export.py ch01 --url http://localhost:8765/madness/ --out /tmp/out --jobs 2 --to bosch
up to bosch: 2 beats
loudness -24.7 LUFS, -6.8 dBTP as the page mixes it; levelled to -16.2 LUFS, -1.7 dBTP (+8.7 dB, limiter at -1.8 dBFS; --lufs -16)
encoder libx264, 2 browsers
open: 338 frames
bosch: 269 frames
/tmp/out/ch01.mp4: -16.3 LUFS, -1.7 dBTP after the AAC encode
/tmp/out/ch01.mp4 (0.3 min, 607 frames, 2 beats; sound peak 0.46) and ch01.srt
real 87.20
user 137.90
sys 20.48
[export_exit_status: 0]
srt_file=/tmp/out/ch01.srt lines=20
$ ffprobe -v error -show_entries format=duration,size -of default=nw=1 /tmp/out/ch01.mp4
duration=20.241000
size=8227713
METRICS jobs=2: video_duration=20.241s real=87.20s user=137.90s sys=20.48s frames=607 render_factor=4.308x parallelism=1.82/4_cores fps=6.96
============================================================
RUN jobs=4 to_beat=bosch
$ time -p uv run --with playwright --with numpy vendor/Papermorph/.claude/skills/papermorph/scripts/export.py ch01 --url http://localhost:8765/madness/ --out /tmp/out --jobs 4 --to bosch
up to bosch: 2 beats
loudness -24.7 LUFS, -6.8 dBTP as the page mixes it; levelled to -16.2 LUFS, -1.7 dBTP (+8.7 dB, limiter at -1.8 dBFS; --lufs -16)
encoder libx264, 4 browsers
open: 338 frames
bosch: 269 frames
/tmp/out/ch01.mp4: -16.3 LUFS, -1.7 dBTP after the AAC encode
/tmp/out/ch01.mp4 (0.3 min, 607 frames, 2 beats; sound peak 0.46) and ch01.srt
real 86.63
user 145.34
sys 22.44
[export_exit_status: 0]
srt_file=/tmp/out/ch01.srt lines=20
$ ffprobe -v error -show_entries format=duration,size -of default=nw=1 /tmp/out/ch01.mp4
duration=20.241000
size=8227713
METRICS jobs=4: video_duration=20.241s real=86.63s user=145.34s sys=22.44s frames=607 render_factor=4.280x parallelism=1.94/4_cores fps=7.01
[exit_status: 0]
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
طبق دستور صریح فاز ۲ («این بنچمارک را هرگز روی رانتایم خود Colab نگیر... این فاز فقط کد و سنجهٔ سنجش را آماده می‌کند و بنچمارک واقعی در فاز ۶، درون کانتینر، گرفته می‌شود. اگر برای سالم بودن زنجیره یک اجرای کوتاه در Colab لازم داری، دو قید دارد: با `--to <دومین بیت>` فقط چند بیت بگیر، و `--jobs` را هرگز بیشتر از `nproc` نده»):
1. `chromium-ok` چاپ شود و `CHROME` خالی نباشد: **پاس** (`CHROME=/root/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome` و `chromium-ok` در خطوط ۳۰ و ۳۱ خروجی).
2. `server:200`: **پاس** (`server:200` در خط ۳۲ خروجی).
3. `export.py` با `exit status` صفر تمام شود و خودش نام انکدر و تعداد مرورگر را چاپ کند: **پاس** (`encoder libx264, 2 browsers` با `[export_exit_status: 0]` و `encoder libx264, 4 browsers` با `[export_exit_status: 0]`).
4. `ch01.mp4` و `ch01.srt` ساخته شوند و `ffprobe` طول واقعی خروجی را بدهد: **پاس** (`duration=20.241000` و `size=8227713` برای ۲ بیت اول با `--to bosch`، و `srt_file=/tmp/out/ch01.srt lines=20`؛ بنچمارک کامل ۵۲۹ ثانیه‌ای با `--jobs 4` و `--jobs 8` طبق دستور در فاز ۶ روی Cloud Run job با ۸ هسته گرفته می‌شود).
5. نسخهٔ `ffmpeg`: **ثبت شد** (`ffmpeg version 4.4.2-0ubuntu0.22.04.1` در خط ۲۹ خروجی؛ هیچ شیمی نوشته نشد و فیلتر صدای `export.py` بدون خطا اجرا شد).
6. سه عدد اجباری (ضریب رندر، نسبت موازی‌سازی در کنار `nproc=4`، و فریم بر ثانیه برای ۶۰۷ فریم): **پاس** (در خطوط `METRICS jobs=2` و `METRICS jobs=4` خروجی بالا ثبت شده‌اند).

### ۶. چه چیزی کار نکرد یا تأیید نشد
بنچمارک کامل کل فصل (`madness/ch01` به طول ~۵۲۹ ثانیه با `--jobs 4` و `--jobs 8`) طبق دستور صریح فاز ۲ روی رانتایم ۴ هسته‌ای Colab گرفته نشد و در فاز ۶ درون کانتینر Cloud Run Job با ۸ vCPU اجرا و ثبت خواهد شد.

### ۷. کامیت
- Branch: `main`
- Commit SHA: `21408315ab0f707f2b9a2e905d2e66ca1b447086`
