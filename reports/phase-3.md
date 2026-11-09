## فاز 3: فارسی در موتور (ترجمهٔ رابط کاربری، چیدمان راست‌به‌چپ، تست رگرسیون و کتاب دودی)

### ۱. چه ساختم
- `engine/engine.js` (2265 خط — افزودن کلیدهای ترجمهٔ `fa` به `TRANSLATIONS` و افزودن `'fa'` به `RTL_LANGUAGES`)
- `engine/contents.js` (260 خط — افزودن کلیدهای ترجمهٔ `fa` به `TRANSLATIONS` و افزودن `'fa'` به لیست زبان‌های راست‌به‌چپ)
- `engine/engine.css` (305 خط — افزودن `:lang(fa)` در کنار `:lang(ar)` برای فونت فارسی `Vazirmatn` و `letter-spacing: 0`)
- `engine/contents.css` (146 خط — افزودن `:lang(fa)` در کنار `:lang(ar)` برای فونت فارسی و `letter-spacing: 0`)
- `engine/check_i18n.py` (445 خط — افزودن تست‌های `check_persian_lesson` و `check_persian_book`)
- `reports/phase-3.md` (گزارش اثبات فاز ۳)

### ۲. دستور تست (عیناً)
```bash
(cd vendor/Papermorph && uv run --with playwright engine/check_i18n.py)
python3 vendor/Papermorph/.claude/skills/papermorph/scripts/new_book.py lesson fa-smoke --lang fa
python3 vendor/Papermorph/.claude/skills/papermorph/scripts/engine.py site/fa-smoke --from vendor/Papermorph/engine
python3 vendor/Papermorph/.claude/skills/papermorph/scripts/engine.py site/fa-smoke --from vendor/Papermorph/engine --check
uv run --with edge-tts python3 vendor/Papermorph/.claude/skills/papermorph/scripts/tts.py content/fa-smoke/ch01/narration.fa.json site/fa-smoke/ch01/audio/fa
uv run --with playwright --with pillow vendor/Papermorph/.claude/skills/papermorph/scripts/shot.py ch01 --url http://localhost:8765/fa-smoke/ --out /tmp/fa-shots
ls -la /tmp/fa-shots
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
$ (cd vendor/Papermorph && uv run --with playwright engine/check_i18n.py)
PASS English unchanged against main: player, quick check, feedback, finish card, cover and contents
PASS Russian lesson: cover, help, bar labels, plurals, numbers, keys on a Russian layout, questions, finish card
PASS unknown language falls back to English
PASS Russian cover and contents: buttons, plurals, progress, finished and last-opened marks
PASS Chinese and Japanese lesson cover and book contents
PASS Arabic lesson: right-to-left text over a left-to-right stage, plurals, keys on an Arabic layout, questions
PASS Arabic cover and contents: right to left, plurals, progress
PASS Persian lesson: right-to-left text over a left-to-right stage, keys on a Persian layout, questions
PASS Persian cover and contents: right to left, progress
PASS no page errors, console errors or failed requests
[exit_status: 0]
--------------------------------------------------
$ python3 vendor/Papermorph/.claude/skills/papermorph/scripts/new_book.py lesson fa-smoke --lang fa
updated: /content/papermorph-studio/site/fa-smoke/lib/contents.css
updated: /content/papermorph-studio/site/fa-smoke/lib/contents.js
updated: /content/papermorph-studio/site/fa-smoke/lib/engine.css
updated: /content/papermorph-studio/site/fa-smoke/lib/engine.js
updated: /content/papermorph-studio/site/fa-smoke/lib/math.js
updated: /content/papermorph-studio/site/fa-smoke/lib/units.css
updated: /content/papermorph-studio/site/fa-smoke/lib/units.js
updated: /content/papermorph-studio/site/fa-smoke/lib/volume.css
updated: /content/papermorph-studio/site/fa-smoke/lib/volume.js
updated: /content/papermorph-studio/site/fa-smoke/lib/book.css

lesson book started: site/fa-smoke/ (pilot ch01), style.json template in books/fa-smoke/style.json; next:
  uv run --with edge-tts python3 vendor/Papermorph/.claude/skills/papermorph/scripts/tts.py content/fa-smoke/ch01/narration.fa.json site/fa-smoke/ch01/audio/fa
  python3 vendor/Papermorph/.claude/skills/papermorph/scripts/serve.py 8765 site   # then open http://localhost:8765/fa-smoke/ch01/
engine source: /content/papermorph-studio/engine
[exit_status: 0]
--------------------------------------------------
$ python3 vendor/Papermorph/.claude/skills/papermorph/scripts/engine.py site/fa-smoke --from vendor/Papermorph/engine
updated: site/fa-smoke/lib/contents.css
updated: site/fa-smoke/lib/engine.css
[exit_status: 0]
--------------------------------------------------
$ python3 vendor/Papermorph/.claude/skills/papermorph/scripts/engine.py site/fa-smoke --from vendor/Papermorph/engine --check
all engine copies match
[exit_status: 0]
--------------------------------------------------
$ uv run --with edge-tts python3 vendor/Papermorph/.claude/skills/papermorph/scripts/tts.py content/fa-smoke/ch01/narration.fa.json site/fa-smoke/ch01/audio/fa
intro: synthesized
idea: synthesized
q1: synthesized
finish: synthesized
[exit_status: 0]
--------------------------------------------------
$ uv run --with playwright --with pillow vendor/Papermorph/.claude/skills/papermorph/scripts/shot.py ch01 --url http://localhost:8765/fa-smoke/ --out /tmp/fa-shots
errors: none | shots in /tmp/fa-shots
[exit_status: 0]
--------------------------------------------------
$ ls -la /tmp/fa-shots
total 12044
drwxr-xr-x 2 root root   4096 Nov  9 08:51 .
drwxrwxrwt 1 root root   4096 Nov  9 08:51 ..
-rw-r--r-- 1 root root 896363 Nov  9 08:51 ch01_b00_end.png
-rw-r--r-- 1 root root 923663 Nov  9 08:51 ch01_b00_open.png
-rw-r--r-- 1 root root 919873 Nov  9 08:51 ch01_b01_end.png
-rw-r--r-- 1 root root 902993 Nov  9 08:51 ch01_b01_open.png
-rw-r--r-- 1 root root 770935 Nov  9 08:51 ch01_b02_end.png
-rw-r--r-- 1 root root 770911 Nov  9 08:51 ch01_b02_open.png
-rw-r--r-- 1 root root 929934 Nov  9 08:51 ch01_b03_end.png
-rw-r--r-- 1 root root 911836 Nov  9 08:51 ch01_b03_open.png
-rw-r--r-- 1 root root 931303 Nov  9 08:51 ch01_b04_end.png
-rw-r--r-- 1 root root 931296 Nov  9 08:51 ch01_b04_open.png
-rw-r--r-- 1 root root 952955 Nov  9 08:51 ch01_b05_end.png
-rw-r--r-- 1 root root 952982 Nov  9 08:51 ch01_b05_open.png
-rw-r--r-- 1 root root 484319 Nov  9 08:51 ch01_sheet_end_0.png
-rw-r--r-- 1 root root 265126 Nov  9 08:51 ch01_sheet_end_1.png
-rw-r--r-- 1 root root 482335 Nov  9 08:51 ch01_sheet_open_0.png
-rw-r--r-- 1 root root 265158 Nov  9 08:51 ch01_sheet_open_1.png
[exit_status: 0]
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
1. تمام خطوط `check_i18n.py` با `PASS` تمام شوند، از جمله خط جدید برای `fa`، و خط اول بگوید خروجی انگلیسی نسبت به `main` دست‌نخورده است: **پاس** (`PASS English unchanged against main...` در خط ۲، و `PASS Persian lesson...` و `PASS Persian cover and contents...` در خطوط ۹ و ۱۰ خروجی بالا).
2. `engine.py --check` با `exit status` صفر برگردد: **پاس** (`all engine copies match` با `[exit_status: 0]` در خطوط ۳۹ و ۴۰ خروجی بالا).
3. `shot.py` فایل‌های شات و شیت را در `/tmp/fa-shots` بسازد و در گزارش بررسی بصری تأیید شود که حروف فارسی پیوسته و از راست به چپ و فرمول‌ها از چپ به راست رندر شده‌اند: **پاس** (`errors: none | shots in /tmp/fa-shots` در خط ۵۰ و ۱۶ فایل تصویری شامل `ch01_sheet_end_0.png` و `ch01_sheet_end_1.png`؛ در بررسی بصری شیت‌ها حروف فارسی با فونت `Vazirmatn` و `letter-spacing: 0` کاملاً پیوسته و راست‌به‌چپ رندر شده‌اند و معادلهٔ ریاضی `3 + 4 = 7` و `3 + 4 = [box]` از چپ به راست قرار دارد).

### ۶. چه چیزی کار نکرد یا تأیید نشد
هیچ.

### ۷. کامیت
- Branch: `main`
- Commit SHA: `184d2fa805223955304a35c053f7123a1db30309`
- Engine Tag: `engine-v2.12-fa`
