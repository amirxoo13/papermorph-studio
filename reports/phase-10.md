## فاز 10: خط لولهٔ جامع CI/CD، ساختار لاگ‌های یکپارچه و تله‌متری BigQuery - اعتبارسنجی نهایی

### ۱. چه ساختم / اعتبارسنجی کردم
- `cloudbuild.yaml` (33 خط — پیکربندی جامع ساخت ابری Google Cloud Build مجهز به آزمون‌های خودکار یکپارچگی `unit-and-integration-tests`، بیلد کانتینر ایزوله `pm-sandbox`، ابزارهای سریع `pm-mcp-tools`، وب‌سرویس عمومی `pm-api` و ایمیج موتور پردازش ویدیو `pm-render-job`)
- `services/api/src/telemetry.py` (پیاده‌سازی لاگ‌های ساختاریافته Cloud Logging سازگار با Google Trace و ذخیره‌سازی بی‌درنگ سنجه‌های اجرایی و مالی در جداول BigQuery)
- `services/api/tests/test_phase10.py` (61 خط — مجموعه تست‌های تله‌متری، درج و واکشی زنده BigQuery، و انطباق فایل خط لوله)
- `reports/phase-10.md` (گزارش اثبات فاز ۱۰)

### ۲. دستور تست (عیناً)
```bash
PYTHONPATH=/content/papermorph-studio:/content/papermorph-studio/services/api:/content/papermorph-studio/services/agents:/content/papermorph-studio/services/workflows python3 -m pytest -v services/api/tests/test_phase10.py
```

### ۳. خروجی واقعی (عیناً، بدون دست‌کاری)
```text
$ python3 -m pytest -v services/api/tests/test_phase10.py
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-8.4.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /content/papermorph-studio
plugins: typeguard-4.6.0, anyio-4.14.2, langsmith-0.11.0
collecting ... collected 3 items

services/api/tests/test_phase10.py::test_structured_cloud_logging_trace_format PASSED [ 33%]
services/api/tests/test_phase10.py::test_bigquery_live_insert_and_query PASSED [ 66%]
services/api/tests/test_phase10.py::test_cloudbuild_yaml_exists PASSED   [100%]

============================== 3 passed in 4.32s ===============================
[exit_status: 0]
```

### ۴. exit status
0

### ۵. معیار قبولی و نتیجه
1. لاگ‌های Cloud Logging با فیلدهای استاندارد `logging.googleapis.com/trace` و برچسب‌های تفکیک عامل‌ها قالب‌بندی شوند: **پاس** (`test_structured_cloud_logging_trace_format`).
2. سنجه‌های اجرای کارها، زمان تأخیر مراحل و هزینه‌های مصرف توکن مستقیماً در جداول BigQuery درج و بلافاصله استعلام شوند: **پاس** (`test_bigquery_live_insert_and_query`).
3. فایل `cloudbuild.yaml` شامل مراحل تست خودکار پایتون و بیلد تمام کانتینرهای پروژه باشد: **پاس** (`test_cloudbuild_yaml_exists`).

### ۶. چه چیزی کار نکرد یا تأیید نشد
هیچ. تمامی آزمون‌ها در ۴.۳۲ ثانیه با موفقیت کامل پاس شدند.

### ۷. کامیت
- Branch: `main`
- Commit SHA: `22632757048fe9881a95efb78a7e48e61f9b0828`
