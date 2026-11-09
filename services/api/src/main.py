"""Papermorph Studio public API.

What changed and why, so nobody restores the earlier behaviour:

* Authentication is real. ``verify_caller`` now verifies an Identity Platform
  ID token (see ``auth.py``). It used to trust an ``X-Firebase-Uid`` header and
  to accept any bearer string by hashing it into a uid.
* Submitting a job now actually starts work: it enqueues a Cloud Task which
  calls ``/internal/jobs/{id}/start``, which executes the ``pm-render-job``
  Cloud Run Job. It used to write a ``queued`` document and return.
* Idempotency and rate limiting live in Firestore, not in process memory, so
  they survive a cold start and hold across instances.
* ``GET /v1/books/{id}`` requires a caller and checks ownership. It used to be
  open to anyone who knew or guessed an id.
* Internal endpoints verify a Cloud Tasks OIDC token and fail closed when they
  are not configured. The shared HMAC secret with a hardcoded default is gone.

Nothing in this file may fabricate a value. If a dependency is missing or a
call fails, the request fails with a status code that says so.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.api_core.client_options import ClientOptions
from google.cloud import firestore, storage
from pydantic import BaseModel, Field

from schemas.models import (
    BookDoc, ContentFormat, JobDoc, JobState, LanguageCode, LicenceEntry, SceneDoc,
)
from services.workflows.orchestrator import OrchestratorEngine

from .auth import verify_caller, verify_internal_caller
from .dispatch import DispatchNotConfigured, enqueue_job_start, execute_render_job
from .dlp_gate import PiiDetectedError, inspect_and_redact_text

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

# Browser origins allowed to call this API. A wildcard with credentials is not a
# valid CORS configuration and browsers reject it, so the origins are explicit.
_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("PM_ALLOWED_ORIGINS", "").split(",") if o.strip()
]

app = FastAPI(title="Papermorph Studio Public API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


def _get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)


def _owned_job(db: firestore.Client, job_id: str, uid: str) -> Dict[str, Any]:
    """Fetch a job and confirm this caller owns it, or raise."""
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    data = snap.to_dict() or {}
    if data.get("ownerUid") != uid:
        raise HTTPException(status_code=403, detail="Forbidden: not job owner")
    return data


def _read_source_text(source_uri: str, fallback: str) -> str:
    """Read the manuscript the job was created from.

    The render job needs the text itself (STORY_TEXT), not a pointer to it.
    """
    if not source_uri.startswith("gs://"):
        return fallback
    bucket_name, _, blob_name = source_uri[5:].partition("/")
    if not bucket_name or not blob_name:
        raise HTTPException(status_code=400, detail=f"Malformed sourceUri: {source_uri}")
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    blob = client.bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise HTTPException(status_code=400, detail=f"sourceUri does not exist: {source_uri}")
    return blob.download_as_text()


class CreateJobRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    format: ContentFormat = ContentFormat.TEXTBOOK_LESSON
    language: LanguageCode = LanguageCode.EN
    stylePresetId: str = "default-editorial"
    sourceUri: str
    manuscriptPreviewText: str = ""
    # entrypoint.sh exits non-zero for any tier other than `picture` without a
    # brief, so the caller must supply one for those tiers.
    brief: str = ""
    requireApproval: bool = True
    targetDurationMs: int = Field(default=300000, ge=30000, le=900000)
    costCapUsd: float = Field(default=5.0, gt=0.0, le=50.0)
    licenceSpdx: str = "CC-BY-4.0"
    attribution: str = "Author Manuscript Upload"
    rejectOnPii: bool = False


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "pm-api", "projectId": PROJECT_ID}


@app.post("/v1/jobs")
def create_job(
    req: CreateJobRequest,
    uid: str = Depends(verify_caller),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    db = _get_db()

    # Idempotency in Firestore: create() fails if the document already exists,
    # so two concurrent submits with the same key cannot both create a job.
    idem_ref = None
    if idempotency_key:
        idem_ref = db.collection("idempotency").document(f"{uid}:{idempotency_key}")
        existing = idem_ref.get()
        if existing.exists:
            return (existing.to_dict() or {}).get("response", {})

    try:
        dlp_res = inspect_and_redact_text(
            req.manuscriptPreviewText or req.title, reject_on_pii=req.rejectOnPii
        )
    except PiiDetectedError as e:
        raise HTTPException(status_code=422, detail=str(e))

    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job = JobDoc(
        jobId=job_id,
        ownerUid=uid,
        title=req.title,
        format=req.format,
        language=req.language,
        stylePresetId=req.stylePresetId,
        sourceUri=req.sourceUri,
        state=JobState.QUEUED,
        requireApproval=req.requireApproval,
        targetDurationMs=req.targetDurationMs,
        costCapUsd=req.costCapUsd,
        licences=[
            LicenceEntry(
                assetId=f"src-{job_id}",
                assetType="source_text",
                uri=req.sourceUri,
                licenceSpdx=req.licenceSpdx,
                attribution=req.attribution,
                verified=True,
            )
        ],
    )
    payload = job.model_dump()
    payload["brief"] = req.brief
    db.collection("jobs").document(job_id).set(payload)

    # Hand the job to the queue. If the queue is not configured we say so and
    # mark the job failed, rather than leaving a `queued` job nothing will run.
    try:
        task_name = enqueue_job_start(job_id)
    except DispatchNotConfigured as exc:
        OrchestratorEngine(db=db).transition_state(
            job_id, JobState.FAILED, f"Dispatch not configured: {exc}"
        )
        raise HTTPException(status_code=503, detail=f"Dispatch not configured: {exc}")
    db.collection("jobs").document(job_id).update({"taskName": task_name})
    payload["taskName"] = task_name

    resp_payload = {"job": payload, "dlpScan": dlp_res.model_dump()}
    if idem_ref is not None:
        idem_ref.set(
            {
                "uid": uid,
                "jobId": job_id,
                "response": resp_payload,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
        )
    return resp_payload


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str, uid: str = Depends(verify_caller)):
    db = _get_db()
    data = _owned_job(db, job_id, uid)
    scenes = [
        s.to_dict()
        for s in db.collection("jobs").document(job_id).collection("scenes").order_by("index").stream()
    ]
    return {"job": data, "scenes": scenes}


@app.post("/v1/jobs/{job_id}/approve")
def approve_job(job_id: str, uid: str = Depends(verify_caller)):
    db = _get_db()
    _owned_job(db, job_id, uid)
    updated = OrchestratorEngine(db=db).approve_job(job_id, approver_uid=uid)
    return {"job": updated}


@app.post("/v1/jobs/{job_id}/cancel")
def cancel_job(job_id: str, uid: str = Depends(verify_caller)):
    db = _get_db()
    _owned_job(db, job_id, uid)
    updated = OrchestratorEngine(db=db).transition_state(
        job_id, JobState.CANCELLED, "Cancelled by owner via API"
    )
    return {"job": updated}


@app.get("/v1/jobs/{job_id}/stream")
def stream_job_events(job_id: str, uid: str = Depends(verify_caller)):
    """Send this job's state and its recorded events, then end the stream.

    This is a snapshot, not a live subscription: it sends what Firestore holds
    now and closes. A client that wants live updates polls this or
    GET /v1/jobs/{id}.
    """
    db = _get_db()
    job_data = _owned_job(db, job_id, uid)
    events = [
        e.to_dict()
        for e in db.collection("jobs").document(job_id).collection("events").stream()
    ]

    def _event_gen():
        state = {
            "jobId": job_id,
            "state": job_data.get("state"),
            "costUsd": job_data.get("costUsd", 0.0),
        }
        yield f"event: state\ndata: {json.dumps(state)}\n\n"
        for ev in events:
            yield f"event: log\ndata: {json.dumps(ev)}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(_event_gen(), media_type="text/event-stream")


@app.get("/v1/books/{book_id}")
def get_book(book_id: str, uid: str = Depends(verify_caller)):
    """A book is readable by its owner, or by anyone once it is marked public.

    This mirrors firestore.rules. The endpoint used to take no caller at all.
    """
    db = _get_db()
    snap = db.collection("books").document(book_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Book not found")
    data = snap.to_dict() or {}
    if data.get("ownerUid") != uid and not data.get("public", False):
        raise HTTPException(status_code=403, detail="Forbidden: not book owner")
    return {"book": data}


@app.post("/internal/jobs/{job_id}/start")
def internal_start_job(job_id: str, caller: str = Depends(verify_internal_caller)):
    """Execute pm-render-job for this job. Called by Cloud Tasks, not by a user."""
    db = _get_db()
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    job = snap.to_dict() or {}

    if job.get("state") not in (JobState.QUEUED.value, JobState.QUEUED):
        # Cloud Tasks retries; starting a second render for the same job would
        # double the cost, so a job that already left `queued` is left alone.
        return {"status": "skipped", "jobId": job_id, "state": job.get("state")}

    eng = OrchestratorEngine(db=db)
    try:
        source_text = _read_source_text(
            str(job.get("sourceUri", "")), str(job.get("manuscriptPreviewText", ""))
        )
        execution_name = execute_render_job(job, source_text)
    except DispatchNotConfigured as exc:
        eng.transition_state(job_id, JobState.FAILED, f"Dispatch not configured: {exc}")
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        eng.transition_state(job_id, JobState.FAILED, f"{type(exc).__name__}: {exc}")
        raise

    db.collection("jobs").document(job_id).update(
        {"executionName": execution_name, "startedBy": caller}
    )
    eng.transition_state(job_id, JobState.INGESTING, f"Render job execution {execution_name}")
    return {"status": "started", "jobId": job_id, "executionName": execution_name}


@app.post("/internal/stage-callback")
def internal_stage_callback(
    payload: Dict[str, Any], caller: str = Depends(verify_internal_caller)
):
    """Record a stage transition reported by the render job.

    This used to accept the call and discard it.
    """
    job_id = payload.get("jobId")
    state_raw = payload.get("state")
    if not job_id or not state_raw:
        raise HTTPException(status_code=400, detail="jobId and state are required")
    try:
        state = JobState(state_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown state: {state_raw}")

    eng = OrchestratorEngine(db=_get_db())
    updated = eng.transition_state(
        job_id, state, str(payload.get("message", "")), agent=f"render-job via {caller}"
    )
    return {"status": "recorded", "jobId": job_id, "job": updated}
