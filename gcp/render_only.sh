#!/usr/bin/env bash
# Render a book that is already finished and shipped inside the image,
# or run the Phase 2/6 in-container render benchmark when BENCH_MODE=1.
# Zero model calls. Zero authoring.
set -euo pipefail

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0484425781}"
PUBLISHED_BUCKET="${PUBLISHED_BUCKET:-gen-lang-client-0484425781-pm-published}"

cd /app/vendor/papermorph

if [[ "${BENCH_MODE:-0}" == "1" ]]; then
  echo "=== [PHASE 6 IN-CONTAINER BENCHMARK: nproc=$(nproc)] ==="
  BENCH_JOBS="${BENCH_JOBS:-4,8}"
  BENCH_ARGS="${BENCH_ARGS:-}"
  python3 /app/bench_render.py --jobs "${BENCH_JOBS}" ${BENCH_ARGS}
fi

if [[ -z "${BOOK_SLUG:-}" ]]; then
  exit 0
fi

CHAPTER="${CHAPTER:-ch01}"
JOBS="${JOBS:-8}"
EXPORT_EXTRA="${EXPORT_EXTRA:-}"

echo "=== [1/5] PRECONDITIONS ==="
test -d "site/${BOOK_SLUG}"   || { echo "FATAL: site/${BOOK_SLUG} is not in this image" >&2; exit 20; }
test -f "site/${BOOK_SLUG}/${CHAPTER}/index.html"   || { echo "FATAL: site/${BOOK_SLUG}/${CHAPTER}/index.html missing" >&2; exit 21; }
echo "book=${BOOK_SLUG} chapter=${CHAPTER} jobs=${JOBS} nproc=$(nproc)"
echo "chapter html bytes: $(stat -c%s "site/${BOOK_SLUG}/${CHAPTER}/index.html")"
echo "img files:   $(find "site/${BOOK_SLUG}/img" -type f 2>/dev/null | wc -l)"
echo "audio files: $(find "site/${BOOK_SLUG}/${CHAPTER}/audio" -type f 2>/dev/null | wc -l)"

echo "=== [2/5] PREVIEW SERVER ==="
python3 .claude/skills/papermorph/scripts/serve.py 8765 site &
SERVE_PID=$!
trap 'kill ${SERVE_PID} 2>/dev/null || true' EXIT
READY=0
for i in $(seq 1 30); do
  if [[ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/ || true)" == "200" ]]; then
    READY=1; echo "server ready (PID=${SERVE_PID})"; break
  fi
  sleep 0.5
done
(( READY == 1 )) || { echo "FATAL: serve.py never returned HTTP 200" >&2; exit 13; }

echo "=== [3/5] CHECK.PY (the engine's own gate) ==="
python3 .claude/skills/papermorph/scripts/check.py "${CHAPTER}"   --url "http://localhost:8765/${BOOK_SLUG}/" 2>&1 | tee /tmp/check.log
if grep -Eiq '[1-9][0-9]*[[:space:]]+(page|console)[[:space:]]+error' /tmp/check.log; then
  echo "FATAL: check.py reported errors" >&2; exit 14
fi

echo "=== [4/5] EXPORT ==="
mkdir -p /tmp/export
START=$(date +%s)
python3 .claude/skills/papermorph/scripts/export.py "${CHAPTER}"   --url "http://localhost:8765/${BOOK_SLUG}/"   --out /tmp/export   --jobs "${JOBS}" ${EXPORT_EXTRA}
END=$(date +%s)
echo "RENDER_WALL_SECONDS=$((END - START))"

test -s "/tmp/export/${CHAPTER}.mp4" || { echo "FATAL: no mp4 produced" >&2; exit 22; }
ls -l /tmp/export/
echo "--- ffprobe ---"
ffprobe -v error -show_entries format=duration,size,bit_rate         -show_entries stream=codec_name,width,height,r_frame_rate         -of default=noprint_wrappers=1 "/tmp/export/${CHAPTER}.mp4"

echo "=== [5/5] UPLOAD ==="
python3 - <<'PYUP'
import os
from pathlib import Path
from google.cloud import storage
slug = os.environ["BOOK_SLUG"]; ch = os.environ.get("CHAPTER", "ch01")
bucket_name = os.environ.get("PUBLISHED_BUCKET", "gen-lang-client-0484425781-pm-published")
bucket = storage.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"]).bucket(bucket_name)
n = 0
for p in sorted(Path("/tmp/export").rglob("*")):
    if p.is_file():
        dest = f"renders/{slug}/{ch}/{p.relative_to('/tmp/export').as_posix()}"
        bucket.blob(dest).upload_from_filename(str(p))
        print(f"gs://{bucket_name}/{dest}  ({p.stat().st_size} bytes)")
        n += 1
print(f"uploaded {n} files")
PYUP
