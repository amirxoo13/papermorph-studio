#!/usr/bin/env bash
set -euo pipefail

: "${BOOK_SLUG:?ERROR: BOOK_SLUG environment variable is required}"
: "${BRIEF:?ERROR: BRIEF environment variable is required}"
: "${TARGET_SECONDS:?ERROR: TARGET_SECONDS environment variable is required}"

PUBLISHED_BUCKET="${PUBLISHED_BUCKET:-gen-lang-client-0484425781-pm-published}"
DEST_PREFIX="gs://${PUBLISHED_BUCKET}/test/${BOOK_SLUG}"

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0484425781}"
export VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
export GOOGLE_GENAI_USE_VERTEXAI="true"

cd /app/vendor/papermorph

CHAPTER_HTML="site/${BOOK_SLUG}/ch01/index.html"
if [[ ! -f "${CHAPTER_HTML}" ]]; then
  echo "FATAL: Scaffold file ${CHAPTER_HTML} missing before run" >&2
  exit 10
fi
TEMPLATE_SIZE=$(stat -c%s "${CHAPTER_HTML}")

echo "================================================================"
echo "=== [STAGE 1/5] STARTING HEADLESS OPENCODE (/papermorph) ==="
echo "BOOK_SLUG=${BOOK_SLUG} | TARGET_SECONDS=${TARGET_SECONDS} | TEMPLATE_SIZE=${TEMPLATE_SIZE}B"
echo "BRIEF=${BRIEF}"
echo "================================================================"

opencode run --command papermorph "${BRIEF}"

echo "================================================================"
echo "=== [STAGE 2/5] VERIFYING AUTHORED CHAPTER & REAL AUDIO FILES ==="
echo "================================================================"

FINAL_HTML_SIZE=$(stat -c%s "${CHAPTER_HTML}")
echo "${CHAPTER_HTML}: template=${TEMPLATE_SIZE}B -> final=${FINAL_HTML_SIZE}B"
if (( FINAL_HTML_SIZE <= TEMPLATE_SIZE )); then
  echo "FATAL: ${CHAPTER_HTML} (${FINAL_HTML_SIZE}B) is not larger than the scaffold template (${TEMPLATE_SIZE}B). Bare template counts as failure." >&2
  exit 11
fi

# Check for real audio files in content/<slug>/ch01/ and/or site/<slug>/ch01/audio/ (where tts.py and sfx.py write)
mkdir -p "content/${BOOK_SLUG}/ch01"
if [[ -d "site/${BOOK_SLUG}/ch01/audio" ]]; then
  cp -rn "site/${BOOK_SLUG}/ch01/audio/"* "content/${BOOK_SLUG}/ch01/" 2>/dev/null || true
fi

AUDIO_COUNT=$(find "content/${BOOK_SLUG}/ch01" "site/${BOOK_SLUG}/ch01" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.ogg" \) -size +100c 2>/dev/null | wc -l)
echo "Verified non-empty audio file count for ch01: ${AUDIO_COUNT}"
if (( AUDIO_COUNT == 0 )); then
  echo "FATAL: No real audio files found in content/${BOOK_SLUG}/ch01/ or site/${BOOK_SLUG}/ch01/." >&2
  exit 12
fi

echo "================================================================"
echo "=== [STAGE 3/5] STARTING LOCAL HTTP SERVER (serve.py 8765 site) ==="
echo "================================================================"
python3 .claude/skills/papermorph/scripts/serve.py 8765 site &
SERVE_PID=$!
trap 'kill ${SERVE_PID} 2>/dev/null || true' EXIT
sleep 2
curl -fsS "http://localhost:8765/${BOOK_SLUG}/ch01/" >/dev/null

echo "================================================================"
echo "=== [STAGE 4/5] RUNNING EXPORT.PY (ch01 --jobs 8) ==="
echo "================================================================"
mkdir -p /tmp/export
python3 .claude/skills/papermorph/scripts/export.py ch01 \
  --url "http://localhost:8765/${BOOK_SLUG}/" \
  --out /tmp/export \
  --jobs 8

ls -lh /tmp/export/
test -s /tmp/export/ch01.mp4
test -s /tmp/export/ch01.srt

echo "================================================================"
echo "=== [STAGE 5/5] UPLOADING SITE & EXPORT TO ${DEST_PREFIX}/ ==="
echo "================================================================"
python3 - <<'PYUPLOAD'
import os
from pathlib import Path
from google.cloud import storage

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
bucket_name = os.environ.get("PUBLISHED_BUCKET", "gen-lang-client-0484425781-pm-published")
book_slug = os.environ["BOOK_SLUG"]

client = storage.Client(project=project_id)
bucket = client.bucket(bucket_name)

uploaded = 0
site_root = Path(f"/app/vendor/papermorph/site/{book_slug}")
for p in sorted(site_root.rglob("*")):
    if p.is_file():
        rel = p.relative_to(site_root).as_posix()
        blob_path = f"test/{book_slug}/site/{rel}"
        bucket.blob(blob_path).upload_from_filename(str(p))
        uploaded += 1

export_root = Path("/tmp/export")
for p in sorted(export_root.rglob("*")):
    if p.is_file():
        rel = p.relative_to(export_root).as_posix()
        blob_path = f"test/{book_slug}/export/{rel}"
        bucket.blob(blob_path).upload_from_filename(str(p))
        uploaded += 1

print(f"Uploaded {uploaded} files to gs://{bucket_name}/test/{book_slug}/{{site,export}}/")
PYUPLOAD

echo "================================================================"
echo "=== [DONE] STEP 7e PIPELINE COMPLETED SUCCESSFULLY ==="
echo "================================================================"
