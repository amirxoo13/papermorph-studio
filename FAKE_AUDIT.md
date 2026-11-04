# FAKE AUDIT

services/render-job/vendor/papermorph/engine.py:60-225 — hand-written 225-line Pillow rectangle drawer and sine-wave WAV synthesizer — must become a real git clone of https://github.com/amirxoo13/Papermorph under services/render-job/vendor/papermorph
services/render-job/src/render_shard.py:14-83 — wrapper calling the hand-written Pillow/sine-wave PapermorphEngine class — must invoke the real Papermorph skill and `.claude/skills/papermorph/scripts/export.py`
services/workflows/papermorph_pipeline.yaml:1-34 — 34-line YAML stub that only assigns a `stages_visited` list and returns static JSON — must make real HTTP/Cloud Run Job calls for each pipeline stage
services/agents/papermorph_agents/agent.py:66-84 — defines `LlmAgent` objects in memory with no HTTP server and no Dockerfile — must be deployed or invoked headlessly via the real Papermorph skill
services/agents/papermorph_agents/agent.py:86-107 — `_grounded_extractive_storyboard` deterministic sentence-splitting fallback when Gemini fails — must be removed so model failures fail loudly without fake fallback
services/agents/papermorph_agents/agent.py:124-135 — `try ... except Exception:` catching Vertex AI errors and substituting `_grounded_extractive_storyboard` — must let exceptions raise and fail the stage loudly
services/mcp-tools/src/main.py:59-66 — `signed_url_create` returns a fabricated string `https://storage.mtls.cloud.google.com/...` — must call `blob.generate_signed_url(version='v4', ...)` with real credentials
services/mcp-tools/src/main.py:69-75 — `docai_extract` downloads plain text and runs `.split('\n\n')` instead of calling Document AI — must call Google Cloud Document AI `DocumentProcessorServiceClient` or real document parser
services/mcp-tools/src/main.py:78-96 — `vertex_search_index` and `vertex_search_query` store chunks in Firestore and score by Python `set.intersection` — must use real Vertex AI Search (`discoveryengine.googleapis.com`) or real vector embeddings
services/mcp-tools/src/main.py:127-132 — `tts_synthesize` catches TTS exceptions and silently falls back to `en-US-Neural2-D` — must fail loudly if the requested voice/language call fails
services/mcp-tools/src/main.py:165-190 — `stt_word_timings` catches all Speech-to-Text exceptions (`except Exception: pass`) and fabricates uniform word timings by dividing duration by word count — must fail loudly without fabricated timings
services/mcp-tools/src/main.py:204-217 — `image_generate` draws a beige 1920x1080 rectangle and text with `PIL.ImageDraw` instead of calling Imagen 3 — must call Vertex AI `imagen-3.0-generate-002` and fail loudly on error
services/mcp-tools/src/main.py:220-229 — `video_clip_generate` and `music_generate` return static dicts without calling Veo or Lyria — must either call the real model or be explicitly disabled rather than returning fake metadata
services/mcp-tools/src/main.py:232-243 — `render_shard_submit` returns a computed list of dict paths in memory without launching any Cloud Run Job — must trigger a real Cloud Run Job execution
services/mcp-tools/src/main.py:253-260 — `contact_sheet_build` saves a blank white `Image.new('RGB', (1920, 1080), color=(255, 255, 255))` PNG — must composite real rendered frames from the output video/book
services/api/src/dlp_gate.py:50-51 — `inspect_and_redact_text` catches Cloud DLP exceptions and silently falls back to local regex — must fail loudly if Cloud DLP API call fails
services/api/src/main.py:175-229 — `POST /v1/jobs` (`create_job`) writes a `queued` document to Firestore and returns without enqueuing a Cloud Task or starting a Workflow — must enqueue a real Cloud Task that drives the pipeline
services/api/src/main.py:300-490 — embedded HTML UI (`STUDIO_HTML`) uses a client-side `setTimeout` demo button or polls a `queued` job that never advances — must reflect real backend execution and embed the real Papermorph HTML5 player
web/src/app/jobs/[jobId]/page.tsx:5-25 — hardcodes `placeholderJob` with `costUsd: 0.142` instead of fetching `/v1/jobs/{jobId}` — must fetch live job state from the API
web/src/app/books/[bookId]/page.tsx:5-20 — hardcodes `/demo/final_1080p.mp4` and empty `scenes={[]}` — must fetch the real published book and embed the real Papermorph player
scripts/run_e2e_smoke.py:92-122 — synthesizes a 4-second 2-shard Pillow video while writing `durationMs=300000` into `BookDoc` and BigQuery — must run the real Papermorph engine and record the true `ffprobe` duration and real API cost
