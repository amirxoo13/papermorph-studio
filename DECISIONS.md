# Architectural & Model Decisions

## Current decisions

Authoritative model and budget facts live in [`CLAUDE.md`](./CLAUDE.md) §3.
This file records the reasoning behind the structural choices.

- **Region** `us-central1`; Firestore `nam5` (multi-region covering it).
- **No GPU on the render job.** A Cloud Run Job task without a GPU may run for
  168 hours; with one, only 1. Rendering is CPU-bound frame capture, so the GPU
  would buy nothing and cost the timeout.
- **One task, not many.** `export.py --jobs 8` already parallelises frame
  capture across eight headless browsers (`frame f % jobs`). Slicing the film
  across Cloud Run tasks would add seams and complexity for no gain.
- **The engine is vendored, never edited.** Everything we add lives outside
  `vendor/`. A Vertex painter was added as our own `paint_vertex.py` rather than
  patching the engine's `paint.py`, so the vendor tree stays byte-identical to
  upstream and can be re-synced at any time.
- **Narration stays on local Edge TTS / Kokoro**, not a paid speech model: it is
  instant, free, and already emits the word-level `timings.js` the beat clock
  needs. A paid path would not improve it.
- **Generated video is never played as video.** Where a clip is used, the
  engine's `video.py` plus `frames.py` turn it into an ink-line sprite sheet on
  the beat clock, because a `<video>` element would break the determinism that
  `export.py`, `check.py` and `scorm.py` all depend on.
- **Quality gates are the engine's own** `lint.py`, `check.py`, `still.py` and
  `safe.py`. We do not invent gates; hand-written ones rejected good work twice.
- **Review rounds are capped, wall-clock time is not.** Three rounds, then stop.
  Capping time kills work mid-write.

---

## Superseded — historical record only

The list below is from an earlier iteration and is **wrong now**. It is kept so
the change is traceable. Do not use any of it.

| Then | Status now |
|---|---|
| `PRO_MODEL: gemini-2.5-pro` | retired 2026-10-20 → `gemini-4-argon` |
| `FLASH_MODEL: gemini-2.5-flash` | retired 2026-10-20 → `gemini-3.8-flash` |
| `IMAGE_MODEL: imagen-3.0-generate-002` | Imagen retired 2026-06-30 → `gemini-3-pro-image` |
| `STT_MODEL: chirp_2` for word timings | not used; `tts.py` emits timings itself |
| `ENABLE_VEO_CLIPS: false, Imagen 3 used` | wrong on both counts; see `CLAUDE.md` §3 |
| 23 ADK agents behind Cloud Workflows | never deployed; authoring runs as OpenCode headless inside the render job |
