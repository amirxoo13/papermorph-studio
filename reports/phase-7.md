## فاز 7: دروازهٔ حریم خصوصی (Cloud DLP) و دفتر کل مجوزها (`dlp_gate.py` و `licence_gate.py`)

### ۱. چه ساختم
- `services/api/src/dlp_gate.py` (75 خط — بازرسی و سانسور اطلاعات حساس شخصی PII با Google Cloud DLP API `dlp_v2.DlpServiceClient` بدون سقوط بی‌صدا روی خطا، به همراه گارد سخت‌گیرانهٔ `PiiDetectedError`)
- `services/api/src/licence_gate.py` (92 خط — اعتبارسنجی SPDX دارایی‌ها در برابر مجوزهای مجاز، مسدودسازی دارایی‌های فاقد مجوز با `UnlicencedAssetError` و تولید خودکار `SOURCES.md` شامل مجوزهای MIT موتور پیپرمورف و Apache-2.0 کتابخانهٔ MathJax)
- `services/api/tests/test_phase7.py` (70 خط — مجموعه تست‌های ۵گانهٔ دروازهٔ DLP و دفتر کل مجوزها)
- `reports/phase-7.md` (گزارش اثبات فاز ۷)

### ۲. دستور تست (عیناً)
```bash
python3 -m pytest -v services/api/tests/test_phase7.py
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
$ python3 -m pytest -v services/api/tests/test_phase7.py
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-8.4.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /content/papermorph-studio
plugins: typeguard-4.6.0, anyio-4.14.2, langsmith-0.11.0
collecting ... collected 5 items

services/api/tests/test_phase7.py::test_dlp_gate_detects_and_redacts_pii PASSED [ 20%]
services/api/tests/test_phase7.py::test_dlp_gate_rejects_when_strict_mode_enabled PASSED [ 40%]
services/api/tests/test_phase7.py::test_licence_ledger_blocks_unlicenced_or_unknown_spdx PASSED [ 60%]
services/api/tests/test_phase7.py::test_licence_ledger_passes_valid_entries_and_generates_sources_md PASSED [ 80%]
services/api/tests/test_phase7.py::test_sources_md_includes_papermorph_mit_and_mathjax_apache2 PASSED [100%]

============================== 5 passed in 1.36s ===============================
[exit_status: 0]
------------------------------------------------------------
LICENCE_GATE: {'verifiedCount': 3, 'papermorphEngineLicence': 'MIT', 'bundledMathJaxLicence': 'Apache-2.0', 'status': 'verified'}
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
1. شناسایی و سانسور اطلاعات حساس (ایمیل، SSN، شماره تلفن) با Cloud DLP (`test_dlp_gate_detects_and_redacts_pii`): **پاس**.
2. مسدودسازی ورودی حاوی PII در حالت سخت‌گیرانه (`test_dlp_gate_rejects_when_strict_mode_enabled`): **پاس**.
3. جلوگیری از انتشار دارایی‌های بدون مجوز یا دارای SPDX نامعتبر (`test_licence_ledger_blocks_unlicenced_or_unknown_spdx`): **پاس**.
4. تأیید مجوزهای معتبر (`CC-BY-4.0`, `OFL-1.1`, `CC0-1.0`, `Proprietary-Vertex-Imagen3`) و تولید `SOURCES.md` حاوی مجوزهای `MIT` و `Apache-2.0`: **پاس** (`5 passed` با `[exit_status: 0]`).

### ۶. چه چیزی کار نکرد یا تأیید نشد
هیچ.

### ۷. کامیت
- Branch: `main`
- Commit SHA: `216181ae885f4a7a9929252007c5591fce9c8ac2`
