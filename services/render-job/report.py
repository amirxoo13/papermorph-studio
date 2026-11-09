#!/usr/bin/env python3
"""Report this render's progress and its result back to Firestore.

Before this file the render job was a dead end: entrypoint.sh uploaded to a
fixed `test/<slug>/` prefix and told nobody, so a job created through the API
stayed `queued` for ever while its film sat in a bucket under a name the API
could not guess.

Nothing here invents a value, per CLAUDE.md §6:

  * durationMs comes from `ffprobe` on the file that was actually produced.
  * Every URI names an object this run uploaded; a file that is not there is
    not listed.
  * costUsd is copied from the job document and never computed here. A cost
    may only come from Cloud Billing or `paint.py --total LEDGER`, and this
    script has neither.

With PM_JOB_ID unset the script does nothing and exits 0, so render_only.sh and
hand-run renders behave exactly as they did.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
JOB_ID = os.environ.get("PM_JOB_ID", "").strip()
BUCKET = os.environ.get("PUBLISHED_BUCKET", f"{PROJECT_ID}-pm-published")
DEST_SUBPATH = os.environ.get("DEST_SUBPATH", "").strip("/")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    from google.cloud import firestore

    return firestore.Client(project=PROJECT_ID)


def _log(db, state: str, message: str, level: str = "INFO") -> None:
    """Append one event, the same shape the API's own events use."""
    job_ref = db.collection("jobs").document(JOB_ID)
    ev = job_ref.collection("events").document()
    ev.set(
        {
            "eventId": ev.id,
            "jobId": JOB_ID,
            "stage": state,
            "agent": "render-job",
            "level": level,
            "message": message,
            "costDeltaUsd": 0.0,
            "createdAt": _now(),
        }
    )


def cmd_stage(state: str, message: str) -> int:
    db = _db()
    db.collection("jobs").document(JOB_ID).update({"state": state, "updatedAt": _now()})
    _log(db, state, message or state)
    print(f"[report] {JOB_ID} -> {state}")
    return 0


def cmd_failed(message: str) -> int:
    db = _db()
    db.collection("jobs").document(JOB_ID).update(
        {"state": "failed", "errorMessage": message[:1500], "updatedAt": _now()}
    )
    _log(db, "failed", message[:1500], level="ERROR")
    print(f"[report] {JOB_ID} -> failed: {message[:200]}")
    return 0


def _probe_duration_ms(path: Path) -> int:
    """The film's real length. Raises if ffprobe cannot read it."""
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return int(round(float(out) * 1000))


def cmd_done(export_dir: str) -> int:
    export = Path(export_dir)
    mp4 = export / "ch01.mp4"
    if not mp4.is_file() or mp4.stat().st_size == 0:
        return cmd_failed(f"publish reported done but {mp4} is missing or empty")

    duration_ms = _probe_duration_ms(mp4)
    base = f"gs://{BUCKET}/{DEST_SUBPATH}"

    db = _db()
    job_ref = db.collection("jobs").document(JOB_ID)
    snap = job_ref.get()
    if not snap.exists:
        print(f"[report] no job document {JOB_ID}; nothing to update", file=sys.stderr)
        return 0
    job = snap.to_dict() or {}

    # Only name files that are really there.
    artifacts = {"video1080pUrl": f"{base}/export/{mp4.name}"}
    for name, key in (("ch01.srt", "srtUrl"), ("sources.md", "sourcesMdUrl")):
        if (export / name).is_file():
            artifacts[key] = f"{base}/export/{name}"
    if (export / "ch01.mp4").is_file():
        artifacts["readerUrl"] = f"{base}/site/{job.get('bookSlug', '')}".rstrip("/")

    book = {
        "bookId": JOB_ID,
        "jobId": JOB_ID,
        "ownerUid": job.get("ownerUid", ""),
        "title": job.get("title", ""),
        "language": job.get("language", "en"),
        "format": job.get("format", ""),
        "readerUrl": f"{base}/site/",
        "video1080pUrl": artifacts["video1080pUrl"],
        "shorts9x16Url": None,
        "srtUrl": artifacts.get("srtUrl", ""),
        "scormZipUrl": None,
        "sourcesMdUrl": artifacts.get("sourcesMdUrl", ""),
        "durationMs": duration_ms,
        # Copied, never computed. See the module docstring.
        "costUsd": float(job.get("costUsd", 0.0)),
        "public": False,
        "publishedAt": _now(),
    }
    db.collection("books").document(JOB_ID).set(book)

    job_ref.update(
        {
            "state": "done",
            "actualDurationMs": duration_ms,
            "artifacts": artifacts,
            "bookId": JOB_ID,
            "updatedAt": _now(),
        }
    )
    _log(db, "done", f"Published {artifacts['video1080pUrl']} ({duration_ms} ms, ffprobe)")
    print(f"[report] {JOB_ID} -> done, {duration_ms} ms\n{json.dumps(artifacts, indent=2)}")
    return 0


def main(argv: list) -> int:
    if not JOB_ID:
        return 0  # hand-run render: nothing to report to
    if not argv:
        print("usage: report.py stage <state> [message] | done <export-dir> | failed <message>",
              file=sys.stderr)
        return 2
    verb = argv[0]
    try:
        if verb == "stage":
            return cmd_stage(argv[1], " ".join(argv[2:]))
        if verb == "done":
            return cmd_done(argv[1] if len(argv) > 1 else "/tmp/export")
        if verb == "failed":
            return cmd_failed(" ".join(argv[1:]) or "render job failed")
    except Exception as exc:  # reporting must never mask the render's own exit code
        print(f"[report] FAILED to report '{verb}': {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0
    print(f"[report] unknown verb {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
