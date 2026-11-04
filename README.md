# Papermorph Studio (`gen-lang-client-0484425781`)

End-to-end multi-agent educational book, 5-minute 1080p lesson video, synced `.srt` subtitles, 9:16 shorts, and SCORM 1.2/2004 production studio built on Google Cloud (`us-central1`).

## Architecture Highlights
- **Orchestration**: Cloud Workflows + Eventarc + Cloud Tasks + Pub/Sub DLQ + Cloud Scheduler Reaper
- **Multi-Agent System**: 23 specialized Google ADK agents (`google-adk`, `google-genai`) with hard per-job cost guards (`budget.py`)
- **MCP Tool Server**: Cloud Run `FastMCP` server (`services/mcp-tools`) + network-isolated Python sandbox (`services/sandbox`)
- **Render Engine**: Vendored `amirxoo13/Papermorph` (`services/render-job`) running 10 parallel Cloud Run Job shards (`--start-ms`, `--end-ms`) + `PAPERMORPH_TTS_BACKEND=google`
- **Security**: Per-service least-privilege IAM, Cloud DLP PII scrubbing, Vertex AI Safety/Model Armor, `SOURCES.md` licence ledger
- **Public API & Web**: FastAPI on Cloud Run (`services/api`) + Next.js App Router (`web/` with EN/FA RTL support)
