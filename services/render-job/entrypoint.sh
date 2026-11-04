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

SCENE1_JS="site/${BOOK_SLUG}/ch01/scene1.js"
if [[ ! -f "${SCENE1_JS}" ]]; then
  echo "FATAL: Scaffold file ${SCENE1_JS} missing before run" >&2
  exit 10
fi
SCENE1_TEMPLATE_SIZE=$(stat -c%s "${SCENE1_JS}")

echo "================================================================"
echo "=== [STAGE 1/5] STARTING PERSISTENT HTTP SERVER (serve.py 8765 site) ==="
echo "================================================================"
python3 .claude/skills/papermorph/scripts/serve.py 8765 site &
SERVE_PID=$!
trap 'kill ${SERVE_PID} 2>/dev/null || true' EXIT

SERVER_READY=0
for i in $(seq 1 30); do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8765/" || true)
  if [[ "${HTTP_CODE}" == "200" ]]; then
    SERVER_READY=1
    echo "Preview server ready at http://localhost:8765/ (PID=${SERVE_PID}, HTTP ${HTTP_CODE})"
    break
  fi
  sleep 0.5
done
if (( SERVER_READY == 0 )); then
  echo "FATAL: serve.py failed to return HTTP 200 on http://localhost:8765/" >&2
  exit 13
fi

echo "================================================================"
echo "=== [STAGE 2/5] STARTING HEADLESS OPENCODE (/papermorph) ==="
echo "BOOK_SLUG=${BOOK_SLUG} | TARGET_SECONDS=${TARGET_SECONDS} | SCENE1_TEMPLATE_SIZE=${SCENE1_TEMPLATE_SIZE}B"
echo "BRIEF=${BRIEF}"
echo "================================================================"

opencode run --command papermorph "${BRIEF}"

echo "================================================================"
echo "=== [STAGE 3/5] VERIFYING AUTHORED CHAPTER (AUDIO, TIMINGS, SCENE1, CHECK.PY) ==="
echo "================================================================"

# Ensure content/${BOOK_SLUG}/ch01 has any audio generated into site/${BOOK_SLUG}/ch01/audio
mkdir -p "content/${BOOK_SLUG}/ch01"
if [[ -d "site/${BOOK_SLUG}/ch01/audio" ]]; then
  cp -rn "site/${BOOK_SLUG}/ch01/audio/"* "content/${BOOK_SLUG}/ch01/" 2>/dev/null || true
fi

# Gate 1: content/${BOOK_SLUG}/ch01/ contains audio files with non-zero size
CONTENT_AUDIO_COUNT=$(find "content/${BOOK_SLUG}/ch01" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.ogg" \) -size +0c 2>/dev/null | wc -l)
echo "Gate 1 - Non-zero audio files in content/${BOOK_SLUG}/ch01/: ${CONTENT_AUDIO_COUNT}"
if (( CONTENT_AUDIO_COUNT == 0 )); then
  echo "FATAL [Gate 1]: content/${BOOK_SLUG}/ch01/ contains zero non-empty audio files." >&2
  exit 11
fi

# Gate 2: timings.js exists
TIMINGS_COUNT=$(find "site/${BOOK_SLUG}" "content/${BOOK_SLUG}" "books/${BOOK_SLUG}" -name "timings.js" -size +0c 2>/dev/null | wc -l)
echo "Gate 2 - Non-empty timings.js files found: ${TIMINGS_COUNT}"
if (( TIMINGS_COUNT == 0 )); then
  echo "FATAL [Gate 2]: timings.js does not exist or is empty." >&2
  exit 12
fi

# Gate 3: site/${BOOK_SLUG}/ch01/scene1.js is larger than its scaffold and defines real beats
if [[ ! -f "${SCENE1_JS}" ]]; then
  echo "FATAL [Gate 3]: ${SCENE1_JS} is missing." >&2
  exit 14
fi
SCENE1_FINAL_SIZE=$(stat -c%s "${SCENE1_JS}")
echo "Gate 3 - ${SCENE1_JS}: scaffold=${SCENE1_TEMPLATE_SIZE}B -> final=${SCENE1_FINAL_SIZE}B"
if (( SCENE1_FINAL_SIZE <= SCENE1_TEMPLATE_SIZE )); then
  echo "FATAL [Gate 3]: ${SCENE1_JS} (${SCENE1_FINAL_SIZE}B) is not larger than its scaffold (${SCENE1_TEMPLATE_SIZE}B)." >&2
  exit 15
fi
if ! grep -Eq 'beats|beat[[:space:]]*\(|narration|voice|clips' "${SCENE1_JS}"; then
  echo "FATAL [Gate 3]: ${SCENE1_JS} does not define real beats." >&2
  exit 16
fi

# Gate 4: python3 .claude/skills/papermorph/scripts/check.py passes
echo "Gate 4 - Running Papermorph check.py..."
if python3 .claude/skills/papermorph/scripts/check.py --help 2>&1 | grep -q -- "--url"; then
  python3 .claude/skills/papermorph/scripts/check.py ch01 --url "http://localhost:8765/${BOOK_SLUG}/"
else
  python3 .claude/skills/papermorph/scripts/check.py "http://localhost:8765/${BOOK_SLUG}/ch01/"
fi

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
echo "=== [DONE] STEP 7g PIPELINE COMPLETED SUCCESSFULLY ==="
echo "================================================================"
