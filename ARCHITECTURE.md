# System Architecture

```mermaid
graph TD
  User[User / Next.js Web EN+FA] -->|Firebase Auth + App Check| API[Cloud Run: FastAPI Public API]
  User -->|Signed URL PUT| RawGCS[(GCS: raw-uploads)]
  RawGCS -->|Eventarc Finalize| WF[Cloud Workflows: Job Orchestrator]
  API -->|Enqueue| Tasks[Cloud Tasks: per-user rate limit]
  Tasks --> WF
  WF -->|Invoke ADK| Agents[23 Google ADK Agents + Cost Guard]
  Agents -->|Streamable HTTP MCP| MCP[Cloud Run: FastMCP Tool Server]
  MCP -->|Internal Ingress Only| Sandbox[Cloud Run: Isolated Python Sandbox]
  WF -->|Execute 1 Task: 8 vCPU, --jobs 8| Render[Cloud Run Job: Papermorph export.py]
  Render -->|Publish MP4 + SRT + HTML5 + SCORM| PubGCS[(GCS: published)]
  Agents & WF & Render -->|State & Events| FS[(Firestore Native + 90d TTL)]
```

## Rendering Design
- **Single Cloud Run Job Task (`8 vCPU`, `--jobs 8`, no GPU)**: `services/render-job` packages the upstream `amirxoo13/Papermorph` repository under `/app/vendor/papermorph`. A single 8-vCPU task starts `serve.py` locally and runs `.claude/skills/papermorph/scripts/export.py --jobs 8`, which launches 8 parallel headless browsers (`frame f % 8`) and streams frames into `ffmpeg` in order.
