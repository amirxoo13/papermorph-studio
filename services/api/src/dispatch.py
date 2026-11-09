"""Queueing a submitted job and executing the real Cloud Run render job.

``POST /v1/jobs`` used to write a ``queued`` document to Firestore and return,
so a submitted job never advanced: nothing enqueued it and nothing ran. The
Cloud Tasks queue and the ``pm-render-job`` Cloud Run Job both already exist --
only the link between them was missing.

The chain is:

    POST /v1/jobs  ->  Cloud Task (OIDC)  ->  POST /internal/jobs/{id}/start
                                          ->  run_v2 execute pm-render-job

The hop through Cloud Tasks is not decoration: a Cloud Run *request* is capped
at 60 minutes while a render takes longer, so the HTTP request may not wait for
the work. It also gives retries and a rate limit for free.

The env vars below are the ones ``services/render-job/entrypoint.sh`` actually
reads -- BOOK_SLUG, BOOK_TITLE, STORY_TEXT and TARGET_SECONDS are mandatory
there (the container exits non-zero without them), and any TIER other than
``picture`` additionally requires BRIEF.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

# google.cloud.run_v2 and tasks_v2 are imported inside the two functions that
# call them, so the pure mapping below (render_job_env, _slugify) can be
# imported and tested without the cloud SDKs present.

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
REGION = os.environ.get("PM_REGION", "us-central1")
# Verified live on 2026-11-09 with `gcloud tasks queues list --location=us-central1`:
# the queue that exists in the project is papermorph-job-queue. The previous
# default, "pm-job-queue", was a guess and every enqueue would have failed.
TASKS_QUEUE = os.environ.get("PM_TASKS_QUEUE", "papermorph-job-queue")
RENDER_JOB = os.environ.get("PM_RENDER_JOB", "pm-render-job")
PUBLISHED_BUCKET = os.environ.get("PM_PUBLISHED_BUCKET", f"{PROJECT_ID}-pm-published")

SERVICE_BASE_URL = os.environ.get("PM_SERVICE_BASE_URL", "").rstrip("/")
TASKS_INVOKER_SA = os.environ.get("PM_TASKS_INVOKER_SERVICE_ACCOUNT", "")

# ContentFormat -> the engine's own tier name. new_book.py takes exactly these
# four: lesson, picture, documentary, shorts.
FORMAT_TO_TIER = {
    "textbook_lesson": "lesson",
    "picture_book": "picture",
    "documentary": "documentary",
    "short": "shorts",
    # Legacy value that collapsed documentary and shorts into one.
    "documentary_shorts": "documentary",
}


class DispatchNotConfigured(RuntimeError):
    """Raised when the queue or the job target is not configured."""


def _slugify(title: str, job_id: str) -> str:
    """A book slug the engine accepts: lowercase, hyphen separated, never empty."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-")
    return slug or f"job-{job_id[-8:]}"


def render_job_env(job: Dict[str, Any], source_text: str) -> Dict[str, str]:
    """The environment overrides for one execution of pm-render-job."""
    fmt = str(job.get("format", ""))
    if fmt not in FORMAT_TO_TIER:
        raise DispatchNotConfigured(
            f"Unknown content format '{fmt}': cannot choose an engine tier. "
            f"Known: {sorted(FORMAT_TO_TIER)}"
        )
    tier = FORMAT_TO_TIER[fmt]
    target_seconds = max(1, int(job.get("targetDurationMs", 300_000)) // 1000)
    env = {
        "BOOK_SLUG": _slugify(str(job.get("title", "")), str(job.get("jobId", ""))),
        "BOOK_TITLE": str(job.get("title", "")),
        "STORY_TEXT": source_text,
        "TARGET_SECONDS": str(target_seconds),
        "TIER": tier,
        "LANGUAGE": str(job.get("language", "en")),
        "PUBLISHED_BUCKET": PUBLISHED_BUCKET,
        "PM_JOB_ID": str(job.get("jobId", "")),
        "COST_CAP_USD": str(job.get("costCapUsd", 5.0)),
    }
    # entrypoint.sh exits 15 for any tier other than `picture` without a BRIEF.
    brief = job.get("brief") or ""
    if brief:
        env["BRIEF"] = str(brief)
    elif tier != "picture":
        raise DispatchNotConfigured(
            f"TIER={tier} requires an explicit brief; the engine's built-in brief is picture-book only"
        )
    return env


def execute_render_job(job: Dict[str, Any], source_text: str) -> str:
    """Execute pm-render-job for this job and return the execution name."""
    from google.cloud import run_v2

    env = render_job_env(job, source_text)
    client = run_v2.JobsClient()
    name = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/{RENDER_JOB}"
    overrides = run_v2.RunJobRequest.Overrides(
        container_overrides=[
            run_v2.RunJobRequest.Overrides.ContainerOverride(
                env=[run_v2.EnvVar(name=k, value=v) for k, v in env.items()]
            )
        ]
    )
    operation = client.run_job(request=run_v2.RunJobRequest(name=name, overrides=overrides))
    # run_job returns a long-running operation; its metadata carries the
    # execution name, which is what identifies the run in logs and in the
    # console. We do not wait for the render to finish here.
    metadata = operation.metadata
    execution_name = getattr(metadata, "name", "") or ""
    return execution_name


def enqueue_job_start(job_id: str) -> str:
    """Put one Cloud Task on the queue that will start this job. Returns the task name."""
    from google.cloud import tasks_v2

    if not SERVICE_BASE_URL or not TASKS_INVOKER_SA:
        raise DispatchNotConfigured(
            "set PM_SERVICE_BASE_URL and PM_TASKS_INVOKER_SERVICE_ACCOUNT so Cloud Tasks "
            "can call this service with an OIDC token"
        )
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(PROJECT_ID, REGION, TASKS_QUEUE)
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=f"{SERVICE_BASE_URL}/internal/jobs/{job_id}/start",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"jobId": job_id}).encode("utf-8"),
            oidc_token=tasks_v2.OidcToken(
                service_account_email=TASKS_INVOKER_SA,
                audience=SERVICE_BASE_URL,
            ),
        ),
        # One task per job id, so a retried submit cannot start two renders.
        name=client.task_path(PROJECT_ID, REGION, TASKS_QUEUE, f"start-{job_id}"),
    )
    created = client.create_task(request=tasks_v2.CreateTaskRequest(parent=parent, task=task))
    return created.name
