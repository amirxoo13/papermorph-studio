# Papermorph Studio (`gen-lang-client-0484425781`)

Work-in-progress Google Cloud repository wrapping the upstream [Papermorph](https://github.com/amirxoo13/Papermorph) engine (`810e9bca280be2a02cb6b184fa620afc86fc370e`, vendored under `services/render-job/vendor/papermorph`).

For a line-by-line inventory of every stub, fake fallback, and unimplemented integration in this repository, see **[`FAKE_AUDIT.md`](./FAKE_AUDIT.md)**.

---

## Current status

### What works today

1. **Vendored upstream Papermorph repository (`services/render-job/vendor/papermorph`)**: Real clone of `https://github.com/amirxoo13/Papermorph` at commit `810e9bca280be2a02cb6b184fa620afc86fc370e` committed as a plain directory (6,341 files, including `engine/`, `site/`, `AGENTS.md`, `.claude/skills/papermorph/SKILL.md`, and `.claude/skills/papermorph/scripts/export.py`).
2. **GCP foundation in `gen-lang-client-0484425781` (`us-central1` / `nam5`)**:
   - Cloud Billing budget `billingAccounts/01A7F9-B29FE7-D2A289/budgets/f0ef3d0b-e087-4aa0-b69d-01f50ce3c857` (100 EUR, 25/50/75/90% thresholds).
   - Three GCS buckets (`gen-lang-client-0484425781-pm-raw-uploads`, `-pm-work`, `-pm-published`).
   - Firestore Native `(default)` database in `nam5` with 3 composite indexes and a TTL policy on `events.expireAt`.
   - BigQuery dataset `papermorph_analytics` (`job_runs`, `stage_metrics`, `cost_ledger`).
   - Secret Manager secret `papermorph-internal-hmac`.
3. **Deployed Cloud Run services (HTTP 200 `/healthz`)**:
   - `pm-api`: FastAPI service (`services/api/src/main.py`) that reads/writes Firestore `jobs` and `books` documents.
   - `pm-mcp-tools`: FastAPI/FastMCP server (`services/mcp-tools/src/main.py`) exposing 22 tool endpoints, of which GCS read/write/list, Firestore updates, Cloud TTS synthesis (`tts_synthesize`), FFmpeg concat (`ffmpeg_concat`), `.srt` writer (`srt_write`), and SCORM zipping (`scorm_package`) perform real operations.
   - `pm-sandbox`: FastAPI service (`services/sandbox/src/main.py`) that runs `python3 -I` subprocesses with `socket` monkey-patched to raise `PermissionError`.
4. **Shared schemas & cost tracker**:
   - `schemas/models.py`: Pydantic models (`JobDoc`, `SceneDoc`, `EventDoc`, `BookDoc`, `LicenceEntry`) and state-transition validator.
   - `services/agents/papermorph_agents/budget.py` & `duration.py`: Firestore token/cost accumulator (`CostTracker`) and scene duration scaling helper.

### What does not work today

1. **No end-to-end job execution from `POST /v1/jobs`**: `create_job` in `services/api/src/main.py` writes a `state: "queued"` document to Firestore and returns. It does not enqueue a Cloud Task, publish an event, or trigger Cloud Workflows. Jobs created via the API or UI stay in `queued` forever unless mutated manually by a test script.
2. **The "23 agents" are stubs**:
   - `services/agents/papermorph_agents/sub_agents/*.py` consists of 23 two-line files that only re-export `AGENT_REGISTRY[name]`.
   - `services/agents/papermorph_agents/agent.py` loops over a 23-item dictionary (`AGENT_SPECS`) to instantiate 23 bare `LlmAgent` objects with a 3-sentence prompt and no bound tools, plus 1 root `LlmAgent` (`root_agent`). Only a single helper function (`run_live_planning_pipeline`) ever calls `client.models.generate_content`, and on any exception it silently falls back to `_grounded_extractive_storyboard` (deterministic sentence splitting).
   - `services/agents` has **no `Dockerfile`**, no HTTP server, and is **not deployed** to Cloud Run.
3. **`pm-render-job` is broken and does not use the real Papermorph engine**:
   - `services/render-job/src/render_shard.py` still imports the deleted hand-written Pillow/sine-wave classes (`from papermorph import PapermorphEngine, RenderSpec, SceneSpec`) that were removed in commit `60dab18`.
   - Upstream `.claude/skills/papermorph/scripts/export.py` renders a complete HTML book directory (`site/<slug>/index.html`) via headless Playwright + FFmpeg; it has **no `--start-ms` or `--end-ms` flags** and does not support time-sliced sharding today (sharded export is planned work, not implemented).
4. **Cloud Workflow (`services/workflows/papermorph_pipeline.yaml`) is a 34-line stub**: It assigns a static list `stages_visited` in memory and returns JSON without making a single HTTP request or Cloud Run Job call.
5. **Multiple MCP tools in `services/mcp-tools/src/main.py` are fake or have silent fake fallbacks** (detailed in [`FAKE_AUDIT.md`](./FAKE_AUDIT.md)):
   - `image_generate` draws a flat beige 1920x1080 rectangle with `PIL.ImageDraw` instead of calling Imagen 3.
   - `contact_sheet_build` writes a blank white 1920x1080 PNG.
   - `signed_url_create` returns a fabricated string (`https://storage.mtls.cloud.google.com/...`) instead of a real V4 signed URL.
   - `docai_extract` downloads UTF-8 text and runs `.split("\n\n")` instead of calling Document AI.
   - `vertex_search_index` / `vertex_search_query` store chunks in Firestore and rank them with Python `set.intersection` instead of Vertex AI Search.
   - `stt_word_timings` catches all Speech-to-Text exceptions (`except Exception: pass`) and fabricates uniform word timestamps by dividing duration by word count.
   - `tts_synthesize` catches TTS exceptions and silently substitutes `en-US-Neural2-D`.
   - `video_clip_generate`, `music_generate`, and `render_shard_submit` return static dictionaries without calling Veo, Lyria, or Cloud Run Jobs.
6. **DLP gate (`services/api/src/dlp_gate.py`) silently falls back to regex**: Catching `Exception` on `dlp_v2.DlpServiceClient` suppresses API errors and falls back to 4 local regular expressions.
7. **`web/` is a 9-file static skeleton, not a working frontend**:
   - `web/src/app/jobs/[jobId]/page.tsx` and `web/src/app/books/[bookId]/page.tsx` render hardcoded placeholder objects (`costUsd: 0.142`, `/demo/final_1080p.mp4`, `scenes={[]}`) and never call the backend API.
   - `web/` is not deployed to Firebase App Hosting or Cloud Run.
   - The HTML served at `GET /` and `GET /studio` by `services/api/src/main.py` uses a client-side `setTimeout` demo loop (`runLiveDemo`) and submits jobs that remain stuck in `queued`.

---

## Repository Layout

- `FAKE_AUDIT.md` — Line-numbered audit of every stub and fake implementation awaiting replacement.
- `infra/` — Terraform definitions for APIs, budgets, GCS buckets, Firestore indexes/TTL, Artifact Registry, Pub/Sub, Cloud Tasks, Secret Manager, BigQuery, and the stub Cloud Workflow.
- `schemas/` — Pydantic models (`models.py`), exported JSON schemas (`*.schema.json`), and `test_phase2.py`.
- `services/render-job/vendor/papermorph/` — Vendored upstream `amirxoo13/Papermorph` (`810e9bca280b`, MIT license; bundled MathJax under `engine/vendor/mathjax` is Apache-2.0).
- `services/render-job/src/render_shard.py` — Broken wrapper awaiting rewrite to invoke the real Papermorph skill and `export.py`.
- `services/agents/` — Undeployed Python package (`papermorph_agents`) containing `budget.py`, `duration.py`, `agent.py`, and 23 two-line re-export files in `sub_agents/`.
- `services/mcp-tools/` — FastAPI/FastMCP container (`pm-mcp-tools`) with a mix of real GCS/TTS/FFmpeg tools and stubbed tools (see [`FAKE_AUDIT.md`](./FAKE_AUDIT.md)).
- `services/sandbox/` — FastAPI container (`pm-sandbox`) executing Python code in `python3 -I` with socket egress blocked.
- `services/api/` — FastAPI container (`pm-api`) serving `/v1/jobs`, `/v1/books`, `/healthz`, and the inline HTML studio page.
- `services/workflows/` — 34-line stub `papermorph_pipeline.yaml` and Python helper `orchestrator.py`.
- `services/reaper/` & `services/dlq-drainer/` — Local Python functions (`reap_stuck_jobs`, `process_dlq_message`), not deployed as Cloud Run services.
- `web/` — Undeployed Next.js skeleton with hardcoded placeholder props.
