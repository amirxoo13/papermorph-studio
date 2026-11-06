# Papermorph Studio

A Google Cloud platform that turns a story into an animated, narrated film.

It wraps the open-source **[Papermorph](https://github.com/DozenTwelve/Papermorph)**
engine by DozenTwelve (MIT; the bundled MathJax is Apache-2.0). The engine is
vendored, unmodified, at `services/render-job/vendor/papermorph`, pinned to
upstream commit `342e272648e06a6163224a6177bccc83517d7fea` and verified
byte-for-byte against it (7,259 files, empty full-tree hash manifest diff).

## What it makes

Papermorph authors four kinds of film, all of them animation: painted sets and
jointed paper puppets on an SVG stage, moving on a beat clock locked to the
narration's word timings.

| Tier | Stage | What it is |
|---|---|---|
| `lesson` | 1600×900 | a taught chapter, with questions, exportable as SCORM |
| `picture` | 1600×900 | a picture book from a story, a joke or a fairy tale |
| `documentary` | 1600×900 | a narrated film from found and generated pictures |
| `shorts` | 900×1600 | one point, under three minutes, upright for a phone feed |

## How a film is made

```
story  ->  gemini-4-argon authors site/<book>/chNN/
       ->  paint_vertex.py paints the sets and the cast
       ->  tts.py records the narration and writes word-level timings.js
       ->  lint.py / check.py / still.py / safe.py gate it, up to 3 review rounds
       ->  export.py renders deterministically by seeking the clock
       ->  MP4 + SRT (+ SCORM for lessons) in Cloud Storage
```

`export.py` is deterministic: it renders by seeking the beat clock rather than
playing, so a re-render of the same page is identical. It parallelises
internally across headless browsers (`frame f % jobs`), piping JPEG frames
straight into FFmpeg over `image2pipe` — no frame is ever written to disk — and
levels loudness to −16 LUFS.

## Render architecture

One Cloud Run Job task, 8 vCPU, 32 GiB, **no GPU** — a GPU would cap the task
timeout at one hour instead of 168. `export.py --jobs 8` already parallelises
frame capture across eight browsers on the one machine, so splitting the work
across tasks would add seams for nothing.

```
Cloud Run Job pm-render-job
  entrypoint.sh            authoring: scaffold -> serve.py -> OpenCode -> gates -> export
  render_only.sh           RENDER_ONLY=1: render a finished book, zero model calls
    serve.py 8765 site
    check.py <chapter> --url http://localhost:8765/<book>/
    export.py <chapter> --url http://localhost:8765/<book>/ --out <OUT> --jobs 8
  -> <OUT>/<chapter>.mp4 and <OUT>/<chapter>.srt, uploaded to gs://…-pm-published
```

### Measured render performance

Cloud Run has no hardware H.264 encoder, so FFmpeg uses libx264.

| Book | Pictures | Film | Frames | Render | Ratio |
|---|---|---|---|---|---|
| `tulip-mania` | 17 | 200 s | 5,999 | 224 s | 1.12× realtime |
| `millions-of-cats` | 511 | 385 s | 11,563 | 648 s | 1.66× realtime |

Both passed `check.py` with 0 page errors and 0 console errors in Chromium and
Firefox, at 1920×1080, 30 fps.

## Our own code

Everything outside `vendor/` is ours. Nothing inside it is ever edited.

- `services/render-job/entrypoint.sh` — the authoring pipeline. `TIER` selects
  the tier; any tier other than `picture` requires an explicit `BRIEF`.
- `services/render-job/render_only.sh` — renders a book already finished inside
  the image, with no model calls at all.
- `services/render-job/paint_vertex.py` — a Vertex AI painter with the same
  command line and shared cost ledger as the engine's own `paint_openai.py`. It
  refuses `--q high`, refuses to overwrite without `--force`, waits out HTTP 429
  with bounded backoff, and exits non-zero if the returned image has a pixel
  standard deviation below 1.0, so a blank image can never report success.
- `services/render-job/stories/` — scenarios.

## Models

Authoring runs on `gemini-4-argon`; pictures on `gemini-3-pro-image` and
`gemini-3.1-flash-image`; narration on local Edge TTS or Kokoro, which already
produce word-level timings. All Google models, all on Vertex AI.

The binding constraint is quota, not cost: the image model allows roughly two
requests a minute, so a picture-heavy film is paced by quota.

## Repository history

`FAKE_AUDIT.md` and `DECISIONS.md` are kept as a historical record of an earlier
iteration whose generated code was found to be fabricated. They describe what was
removed and why. **They do not describe the current system** — `CLAUDE.md` does.

## Licence

This repository is MIT. The vendored Papermorph engine is MIT, by DozenTwelve;
its bundled MathJax is Apache-2.0.
