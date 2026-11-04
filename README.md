# Papermorph Studio (`gen-lang-client-0484425781`)

Google Cloud studio wrapping the upstream [Papermorph](https://github.com/amirxoo13/Papermorph) engine (`810e9bca280be2a02cb6b184fa620afc86fc370e`, vendored under `services/render-job/vendor/papermorph`).

For a line-by-line inventory of stubs and unimplemented integrations in this repository, see **[`FAKE_AUDIT.md`](./FAKE_AUDIT.md)**.

## Render Architecture (Single 8-vCPU Task with `--jobs 8`)

Papermorph's `.claude/skills/papermorph/scripts/export.py` renders every frame deterministically by seeking the SVG stage (`1600x900` landscape or `900x1600` upright short) and parallelises internally across `--jobs` headless Chromium/Firefox browsers (`frame f % jobs`), writing frames in order to H.264/AAC via FFmpeg and levelling loudness to `-16 LUFS`.

Because `export.py` already parallelises frame capture across headless browsers on a single machine, external task time-slicing is unnecessary:
- **Cloud Run Job (`pm-render-job`)**: Runs as **one Cloud Run Job task (`--tasks=1`) with 8 vCPU (`--cpu=8 --memory=16Gi`, no GPU)** invoking `export.py <chapter> --url http://localhost:8765/<book>/ --out <OUT> --jobs 8 --fps 30 --height 1080`.
- **Outputs**: Produces `<OUT>/<chapter>.mp4` and `<OUT>/<chapter>.srt` directly from `export.py`, and SCORM packages from `scorm.py`.
