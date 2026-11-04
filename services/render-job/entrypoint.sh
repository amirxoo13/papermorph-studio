#!/usr/bin/env bash
set -euo pipefail

: "${BOOK_SLUG:?ERROR: BOOK_SLUG environment variable is required}"
: "${BRIEF:?ERROR: BRIEF environment variable is required}"
: "${TARGET_SECONDS:?ERROR: TARGET_SECONDS environment variable is required}"

PUBLISHED_BUCKET="${PUBLISHED_BUCKET:-gen-lang-client-0484425781-pm-published}"
DEST_PREFIX="gs://${PUBLISHED_BUCKET}/test/${BOOK_SLUG}"

echo "================================================================"
echo "[STAGE 0/4]PREFLIGHT: BOOK_SLUG=${BOOK_SLUG} TARGET_SECONDS=${TARGET_SECONDS}"
echo "[STAGE 0/4]BRIEF: ${BRIEF}"
echo "================================================================"

cd /app/vendor/papermorph

# Ensure clean target book & export directories
rm -rf "/app/vendor/papermorph/site/${BOOK_SLUG}" /tmp/export
mkdir -p /tmp/export

echo "================================================================"
echo "[STAGE 1/4]OPENCODE_START: Running opencode --command papermorph --model google-vertex/gemini-3.5-flash"
echo "================================================================"
FULL_PROMPT="Target book slug: site/${BOOK_SLUG}/ (chapter ch01, target duration ~${TARGET_SECONDS} seconds). Do not ask clarifying questions; proceed autonomously in headless mode and write all chapter files under site/${BOOK_SLUG}/ including ch01.html. Brief: ${BRIEF}"
opencode run --command papermorph --model google-vertex/gemini-3.5-flash "${FULL_PROMPT}"
echo "[STAGE 1/4]OPENCODE_DONE: Verify site/${BOOK_SLUG} exists"

if [ ! -d "/app/vendor/papermorph/site/${BOOK_SLUG}" ]; then
    echo "[ERROR] site/${BOOK_SLUG} was not created by opencode!" >&2
    ls -la /app/vendor/papermorph/site >&2
    exit 1
fi
ls -la "/app/vendor/papermorph/site/${BOOK_SLUG}"

echo "================================================================"
echo "[STAGE 2/4]SERVE_START: Starting serve.py 8765 site in background"
echo "================================================================"
python3 .claude/skills/papermorph/scripts/serve.py 8765 site > /tmp/serve.log 2>&1 &
SERVE_PID=$!
trap 'kill ${SERVE_PID} 2>/dev/null || true' EXIT

# Wait briefly and verify server is listening
for i in $(seq 1 15); do
    if curl -fsS "http://localhost:8765/" >/dev/null 2>&1; then
        echo "[STAGE 2/4]SERVE_READY: http://localhost:8765/ is up (PID=${SERVE_PID})"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "[ERROR] serve.py failed to start on port 8765" >&2
        cat /tmp/serve.log >&2 || true
        exit 1
    fi
    sleep 1
done

echo "================================================================"
echo "[STAGE 3/4]EXPORT_START: Running export.py ch01 --url http://localhost:8765/${BOOK_SLUG}/ --out /tmp/export --jobs 8"
echo "================================================================"
python3 .claude/skills/papermorph/scripts/export.py ch01 \
    --url "http://localhost:8765/${BOOK_SLUG}/" \
    --out /tmp/export \
    --jobs 8
echo "[STAGE 3/4]EXPORT_DONE: Contents of /tmp/export:"
ls -lh /tmp/export

if [ ! -s "/tmp/export/ch01.mp4" ]; then
    echo "[ERROR] /tmp/export/ch01.mp4 missing or empty!" >&2
    exit 1
fi

echo "================================================================"
echo "[STAGE 4/4]UPLOAD_START: Uploading site/${BOOK_SLUG}/ and /tmp/export/ to ${DEST_PREFIX}/"
echo "================================================================"
python3 - <<'PYEOF'
import os
from pathlib import Path
from google.cloud import storage

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
bucket_name = os.environ.get("PUBLISHED_BUCKET", "gen-lang-client-0484425781-pm-published")
book_slug = os.environ["BOOK_SLUG"]

client = storage.Client(project=project_id)
bucket = client.bucket(bucket_name)

site_dir = Path("/app/vendor/papermorph/site") / book_slug
export_dir = Path("/tmp/export")

uploaded = 0
for f in sorted(site_dir.rglob("*")):
    if f.is_file():
        rel = f.relative_to(site_dir).as_posix()
        blob_path = f"test/{book_slug}/site/{rel}"
        bucket.blob(blob_path).upload_from_filename(str(f))
        print(f"  Uploaded gs://{bucket_name}/{blob_path} ({f.stat().st_size} bytes)")
        uploaded += 1

for f in sorted(export_dir.rglob("*")):
    if f.is_file():
        rel = f.relative_to(export_dir).as_posix()
        blob_path = f"test/{book_slug}/export/{rel}"
        bucket.blob(blob_path).upload_from_filename(str(f))
        print(f"  Uploaded gs://{bucket_name}/{blob_path} ({f.stat().st_size} bytes)")
        uploaded += 1

if uploaded == 0:
    raise RuntimeError("Zero files uploaded!")
print(f"Total uploaded files: {uploaded}")
PYEOF

echo "================================================================"
echo "[STAGE 4/4]UPLOAD_DONE: All artifacts uploaded to ${DEST_PREFIX}/"
echo "================================================================"
