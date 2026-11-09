## فاز 8: وب‌سرویس عمومی FastAPI و چرخهٔ حیات کارها (`services/api`) - پیاده‌سازی و اعتبارسنجی کامل

### ۱. چه ساختم / اعتبارسنجی کردم
- `services/api/src/main.py` (207 خط — نقاط پایانی RESTful شامل `/healthz`, `POST /v1/jobs` با کلید یکتایی و محافظت Cloud DLP, `GET /v1/jobs/{job_id}`, `POST /v1/jobs/{job_id}/approve`, `GET /v1/jobs/{job_id}/stream`, و `POST /v1/jobs/{job_id}/cancel`)
- `services/api/src/main.py` (محافظت از نقاط پایانی داخلی با امضای امنیتی `HMAC-SHA256` از طریق هدرهای `X-PM-Payload` و `X-PM-Signature`)
- `services/api/tests/test_phase8.py` (81 خط — آزمون‌های جامع خودکار برای چرخهٔ حیات کارها، ثبت در Firestore، و امنیت HMAC)
- `reports/phase-8.md` (گزارش اثبات فاز ۸)

### ۲. دستور تست (عیناً)
```bash
PYTHONPATH=/content/papermorph-studio:/content/papermorph-studio/services/api:/content/papermorph-studio/services/agents:/content/papermorph-studio/services/workflows python3 -m pytest -v services/api/tests/test_phase8.py
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
$ python3 -m pytest -v services/api/tests/test_phase8.py
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-8.4.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /content/papermorph-studio
plugins: typeguard-4.6.0, anyio-4.14.2, langsmith-0.11.0
collected 3 items

services/api/tests/test_phase8.py::test_healthz PASSED                   [ 33%]
services/api/tests/test_phase8.py::test_create_get_approve_stream_and_cancel_job_lifecycle PASSED [ 66%]
services/api/tests/test_phase8.py::test_hmac_internal_callback_protection PASSED [100%]

============================== 3 passed in 11.95s ==============================
[exit_status: 0]
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
1. پاسخگویی سریع به نقطهٔ پایانی سلامت `/healthz` با مشخصهٔ سرویس `pm-api`: **پاس** (`test_healthz`).
2. ایجاد کار با محافظت کلید یکتایی (`Idempotency-Key`) و بازگرداندن شناسهٔ کار یکسان در صورت ارسال تکراری: **پاس**.
3. پالایش متن و عنوان پیش‌نمایش دست‌نویس با استفاده از موتور Cloud DLP پیش از درج در دیتابیس: **پاس**.
4. مدیریت انتقال وضعیت‌ها در Firestore (از `QUEUED` به `AWAITING_APPROVAL` و سپس `APPROVED` یا `CANCELLED`): **پاس** (`test_create_get_approve_stream_and_cancel_job_lifecycle`).
5. استریم زندهٔ وضعیت کار از طریق Server-Sent Events (`/stream`): **پاس**.
6. حفاظت از نقاط پایانی فراخوانی داخلی (`/internal/jobs/...`) با اعتبارسنجی امضای رمزنگاری‌شدهٔ HMAC و رد درخواست‌های نامعتبر با کد وضعیت 403: **پاس** (`test_hmac_internal_callback_protection`).

### ۶. چه چیزی کار نکرد یا تأیید نشد
هیچ. تمامی آزمون‌ها در ۱۱.۹۵ ثانیه با موفقیت کامل پاس شدند.

### ۷. کامیت
- Branch: `main`
- Commit SHA: `07f6efea6ca3afed2fe738ffd1912d1db1b946df`
