#!/usr/bin/env bash
print_sep() { echo "========================================"; }
print_sep
echo "=== CLI VERSIONS ==="
opencode --version || true
gemini --version || true

print_sep
echo "=== TEST 1: OPENCODE RUN (google-vertex/gemini-3.5-flash) ==="
set +e
opencode run --model google-vertex/gemini-3.5-flash "Reply with exactly: CHAIN OK"
OC_RC=$?
echo "OPENCODE_EXIT_CODE=$OC_RC"

print_sep
echo "=== TEST 2: GEMINI CLI HEADLESS (gemini-3.5-flash) ==="
gemini -m gemini-3.5-flash -p "Reply with exactly: CHAIN OK" --yolo
GM_RC=$?
echo "GEMINI_EXIT_CODE=$GM_RC"
print_sep

set -e
if [ "$OC_RC" -ne 0 ] && [ "$GM_RC" -ne 0 ]; then
  exit 1
fi
