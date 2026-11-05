#!/usr/bin/env bash
set -euo pipefail

: "${BOOK_SLUG:?ERROR: BOOK_SLUG environment variable is required}"
: "${BOOK_TITLE:?ERROR: BOOK_TITLE environment variable is required}"
: "${STORY_TEXT:?ERROR: STORY_TEXT environment variable is required}"
: "${TARGET_SECONDS:?ERROR: TARGET_SECONDS environment variable is required}"
LANGUAGE="${LANGUAGE:-en}"
OPENCODE_MODEL="${OPENCODE_MODEL:-google-vertex/gemini-3.8-flash}"

PUBLISHED_BUCKET="${PUBLISHED_BUCKET:-gen-lang-client-0484425781-pm-published}"
DEST_PREFIX="gs://${PUBLISHED_BUCKET}/test/${BOOK_SLUG}"

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0484425781}"
export VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
export GOOGLE_GENAI_USE_VERTEXAI="true"

# Ensure every run starts with a completely clean OpenCode session/state directory
rm -rf /root/.local/share/opencode /root/.cache/opencode /tmp/opencode.log /tmp/pre_opencode.marker /tmp/check_output.log /tmp/lint_output.log

cd /app/vendor/papermorph

echo "================================================================"
echo "=== [STAGE 0/5] INITIALIZING BOOK SCAFFOLD FOR ${BOOK_SLUG} ==="
echo "BOOK_TITLE=${BOOK_TITLE} | LANGUAGE=${LANGUAGE} | TARGET_SECONDS=${TARGET_SECONDS} | MODEL=${OPENCODE_MODEL}"
echo "================================================================"

# Clean any pre-existing directories for this slug so every run starts fresh
rm -rf "books/${BOOK_SLUG}" "content/${BOOK_SLUG}" "site/${BOOK_SLUG}"
mkdir -p "books/${BOOK_SLUG}"

python3 - <<'PYSTAGE0'
import json
import os
from pathlib import Path

slug = os.environ["BOOK_SLUG"]
title = os.environ["BOOK_TITLE"]
story_text = os.environ["STORY_TEXT"]
target_seconds = int(os.environ["TARGET_SECONDS"])
lang = os.environ.get("LANGUAGE", "en")
model_id = os.environ.get("OPENCODE_MODEL", "google-vertex/gemini-3.8-flash")

book_dir = Path("books") / slug
book_dir.mkdir(parents=True, exist_ok=True)

# 1. Write books/$BOOK_SLUG/story.md
story_md = f"# {title}\n\n{story_text.strip()}\n"
(book_dir / "story.md").write_text(story_md, encoding="utf-8")

# 2. Write books/$BOOK_SLUG/style.json from the picture-book template
style_obj = {
    "schema": 1,
    "tier": "picture",
    "book": {
        "title": title,
        "slug": slug,
        "language": lang,
        "readers": "young children",
        "pilot": "ch01",
        "target_seconds": target_seconds,
        "chapters": 1,
    },
    "words": [
        f"Make a picture book, one chapter, about {target_seconds} seconds long, from {title} in books/{slug}/story.md. Sets and puppets drawn in code (no painted sets).",
        f"Host model note: OpenCode headless runs all steps in the single conversation model {model_id} without per-subagent model switching; recorded across all models keys per style.md.",
    ],
    "look": f"Warm cut-paper collage picture book with sets and paper puppets drawn entirely in SVG/JS code, target length about {target_seconds} seconds in one chapter (ch01).",
    "voice": {
        "engine": "edge",
        "narrator": {
            "voice": "en-US-AndrewNeural" if lang == "en" else "fa-IR-DilaraNeural",
            "rate": "-4%",
        },
        "cast": {},
    },
    "illustration": {
        "sets": "drawn in code, not painted (no image model calls; paint.py must never be reached)",
        "budget": 0,
        "cast": [],
    },
    "engine": {
        "source": "DozenTwelve/Papermorph",
        "ref": "engine-v2.8",
        "license": "MIT",
    },
    "models": {
        "script": model_id,
        "kit": model_id,
        "scenes": model_id,
        "sound": model_id,
        "director": model_id,
        "reviewers": model_id,
    },
    "approved": [],
}
(book_dir / "style.json").write_text(json.dumps(style_obj, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {book_dir / 'story.md'} ({len(story_md)}B) and {book_dir / 'style.json'} (models={model_id})")
PYSTAGE0

python3 .claude/skills/papermorph/scripts/new_book.py picture "${BOOK_SLUG}" --lang "${LANGUAGE}"

if [[ -z "${BRIEF:-}" ]]; then
  BRIEF="CRITICAL RULE: Your very first action MUST be a tool call (Read books/${BOOK_SLUG}/style.json and books/${BOOK_SLUG}/story.md) — NEVER reply with a text-only greeting, acknowledgment, or plan. You are authoring a Papermorph picture book autonomously in a single non-interactive turn. There is no user: never ask a question, never stop to confirm, never stop before all files are written and verified.

books/${BOOK_SLUG}/style.json and books/${BOOK_SLUG}/story.md already exist, so intake is done. A preview server is already running at http://localhost:8765/ — do not start your own serve.py.

IMPORTANT: new_book.py has already created a scaffold under site/${BOOK_SLUG}/. Those scaffold files are an UNFINISHED TEMPLATE (silent placeholders, no real audio, no timings.js, example 'Red' cast). Do NOT mistake the scaffold for a finished chapter. Before writing any code, inspect one finished picture book on the shelf (for example site/little-red-riding-hood/ch01/index.html, site/little-red-riding-hood/ch01/scene1.js, site/little-red-riding-hood/ch01/timings.js, and site/little-red-riding-hood/lib/cast.js) to see the exact structure of a completed picture book.

Follow references/picture-books/stories.md from step 3 onward for the book slug ${BOOK_SLUG}:
1. Write content/${BOOK_SLUG}/ch01/narration.${LANGUAGE}.json for the story in books/${BOOK_SLUG}/story.md (about ${TARGET_SECONDS} seconds total) and run the Papermorph TTS/audio and timing scripts (edge-tts) so real non-empty audio files (.mp3) and timings.js are generated on disk.
2. Draw the sets in code in books/${BOOK_SLUG}/art/sets.js and paper puppets in site/${BOOK_SLUG}/lib/cast.js, and bake puppets if needed.
3. Author the complete animated scene script(s) and site/${BOOK_SLUG}/ch01/index.html wired to the generated audio and timings.js.
4. Run lint.py and check.py against http://localhost:8765/${BOOK_SLUG}/ and fix every error until 0 errors remain.

STRICT TIME & REVIEW BUDGET:
- Keep it simple and fast: 2 scenes maximum, simple clean SVG sets and puppets, ONE review pass only (run lint.py and check.py once, fix any errors, run them once more to confirm 0 errors, then STOP IMMEDIATELY).
- Do NOT do multiple visual polish rounds, do NOT re-bake or re-record audio once timings.js and audio exist and check.py passes with 0 errors.
- Your entire authoring run MUST finish in under 15 minutes so Stage 4 (export.py) can run."
fi

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
echo "MODEL=${OPENCODE_MODEL} | BOOK_SLUG=${BOOK_SLUG} | TARGET_SECONDS=${TARGET_SECONDS}"
echo "BRIEF=${BRIEF}"
echo "================================================================"

MAX_OPENCODE_ATTEMPTS=3
OPENCODE_SUCCESS=0

for ATTEMPT in $(seq 1 ${MAX_OPENCODE_ATTEMPTS}); do
  echo "--- OpenCode Attempt ${ATTEMPT}/${MAX_OPENCODE_ATTEMPTS} (model=${OPENCODE_MODEL}) ---"
  rm -rf /root/.local/share/opencode /root/.cache/opencode /tmp/opencode.log /tmp/pre_opencode.marker
  touch /tmp/pre_opencode.marker
  sleep 1

  set +e
  opencode run --model "${OPENCODE_MODEL}" --command papermorph "${BRIEF}" 2>&1 | tee /tmp/opencode.log
  OPENCODE_RC=${PIPESTATUS[0]}
  set -e

  echo "================================================================"
  echo "=== OPENCODE ATTEMPT ${ATTEMPT} FINISHED WITH EXIT CODE: ${OPENCODE_RC} ==="
  echo "=== LAST 80 LINES OF /tmp/opencode.log ==="
  tail -n 80 /tmp/opencode.log || true
  echo "================================================================"

  if (( OPENCODE_RC != 0 )); then
    echo "FATAL: opencode exited non-zero (${OPENCODE_RC}) on attempt ${ATTEMPT}. Failing before Stage 3 gates." >&2
    exit 20
  fi

  MODIFIED_FILES_COUNT=$(find "site/${BOOK_SLUG}" "content/${BOOK_SLUG}" "books/${BOOK_SLUG}" -type f -newer /tmp/pre_opencode.marker 2>/dev/null | wc -l)
  TOOL_CALLS_COUNT=$(grep -Ec '(\|[[:space:]]+(Write|Edit|Bash|Read|Glob|Grep|Task|patch|write|edit|bash)|←|⚙)' /tmp/opencode.log || true)
  echo "Attempt ${ATTEMPT} activity check: MODIFIED_FILES_COUNT=${MODIFIED_FILES_COUNT}, TOOL_CALLS_COUNT=${TOOL_CALLS_COUNT}"

  if (( MODIFIED_FILES_COUNT > 0 && TOOL_CALLS_COUNT > 0 )); then
    OPENCODE_SUCCESS=1
    break
  fi

  echo "WARNING: OpenCode attempt ${ATTEMPT}/${MAX_OPENCODE_ATTEMPTS} exited 0 but made no tool calls (count=${TOOL_CALLS_COUNT}) or wrote no files (modified=${MODIFIED_FILES_COUNT})." >&2
done

if (( OPENCODE_SUCCESS == 0 )); then
  echo "FATAL [Exit 21]: OpenCode exited 0 but made no tool calls or wrote no files across all ${MAX_OPENCODE_ATTEMPTS} attempts. Never mistaking no-op for success." >&2
  exit 21
fi

echo "================================================================"
echo "=== [STAGE 3/5] VERIFYING AUTHORED CHAPTER (4 GATES ONLY) ==="
echo "================================================================"

# Gate 1: non-zero audio files in content/${BOOK_SLUG}/ch01/ or site/${BOOK_SLUG}/ch01/audio/ (including subdirectories like en/)
AUDIO_COUNT=$(find "content/${BOOK_SLUG}/ch01" "site/${BOOK_SLUG}/ch01/audio" -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.ogg" \) -size +0c 2>/dev/null | wc -l)
echo "Gate 1 - Non-zero audio files in content/${BOOK_SLUG}/ch01/ or site/${BOOK_SLUG}/ch01/audio/: ${AUDIO_COUNT}"
find "content/${BOOK_SLUG}/ch01" "site/${BOOK_SLUG}/ch01/audio" -type f -size +0c 2>/dev/null || true
if (( AUDIO_COUNT == 0 )); then
  echo "FATAL [Gate 1]: Zero non-empty audio files found in content/${BOOK_SLUG}/ch01/ or site/${BOOK_SLUG}/ch01/audio/." >&2
  exit 11
fi

# Gate 2: timings.js exists and is non-empty
TIMINGS_COUNT=$(find "site/${BOOK_SLUG}" "content/${BOOK_SLUG}" "books/${BOOK_SLUG}" -name "timings.js" -size +0c 2>/dev/null | wc -l)
echo "Gate 2 - Non-empty timings.js files found: ${TIMINGS_COUNT}"
find "site/${BOOK_SLUG}" "content/${BOOK_SLUG}" "books/${BOOK_SLUG}" -name "timings.js" -size +0c 2>/dev/null || true
if (( TIMINGS_COUNT == 0 )); then
  echo "FATAL [Gate 2]: timings.js does not exist or is empty." >&2
  exit 12
fi

# Gate 3: lint.py passes
echo "Gate 3 - Running Papermorph lint.py..."
python3 .claude/skills/papermorph/scripts/lint.py "site/${BOOK_SLUG}" ch01 2>&1 | tee /tmp/lint_output.log

# Gate 4: check.py passes with 0 page errors and 0 console errors
echo "Gate 4 - Running Papermorph check.py..."
python3 .claude/skills/papermorph/scripts/check.py ch01 --url "http://localhost:8765/${BOOK_SLUG}/" 2>&1 | tee /tmp/check_output.log
if grep -Eiq '[1-9][0-9]*[[:space:]]+(page|console)[[:space:]]+error' /tmp/check_output.log; then
  echo "FATAL [Gate 4]: check.py reported non-zero page or console errors." >&2
  exit 14
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
echo "=== [DONE] STEP 7o PIPELINE COMPLETED SUCCESSFULLY ==="
echo "================================================================"
