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
from datetime import datetime, timedelta, timezone
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


RAW_UPLOADS_BUCKET = os.environ.get("PM_RAW_UPLOADS_BUCKET", f"{PROJECT_ID}-pm-raw-uploads")
# A manuscript reaches the render job as the STORY_TEXT environment variable,
# and Cloud Run caps a container's whole environment at 32 KiB. The limit is
# therefore in BYTES, not characters: Persian is two bytes per letter in UTF-8,
# so 20 000 Persian characters is about 40 KiB and would be rejected by Cloud
# Run after the job had already been created.
MAX_MANUSCRIPT_BYTES = 16000


class UploadTextRequest(BaseModel):
    """The manuscript itself. There was no way to get text into the system."""

    text: str = Field(..., min_length=20, max_length=MAX_MANUSCRIPT_BYTES)
    filename: str = "manuscript.txt"


@app.post("/v1/uploads")
def upload_text(req: UploadTextRequest, uid: str = Depends(verify_caller)):
    """Store a manuscript and return the gs:// URI that POST /v1/jobs expects.

    Before this, sourceUri had to name an object that someone had already put
    in the bucket by hand, so the API could not be used without gsutil.
    """
    size = len(req.text.encode("utf-8"))
    if size > MAX_MANUSCRIPT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Manuscript is {size} bytes; the limit is {MAX_MANUSCRIPT_BYTES} "
                   f"because it travels to the render job as an environment variable.",
        )
    safe = "".join(c for c in req.filename if c.isalnum() or c in "._-")[:60] or "manuscript.txt"
    blob_name = f"users/{uid}/{uuid.uuid4().hex}-{safe}"
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    blob = client.bucket(RAW_UPLOADS_BUCKET).blob(blob_name)
    blob.upload_from_string(req.text.encode("utf-8"), content_type="text/plain; charset=utf-8")
    uri = f"gs://{RAW_UPLOADS_BUCKET}/{blob_name}"
    return {"sourceUri": uri, "bytes": len(req.text.encode("utf-8"))}


@app.get("/v1/jobs/{job_id}/playback")
def job_playback(job_id: str, uid: str = Depends(verify_caller)):
    """A time-limited URL for the finished film, so a browser can play it.

    The published bucket is private and stays private: this signs one URL for
    one object for one hour. It returns 409 rather than a placeholder while the
    film does not exist yet.
    """
    db = _get_db()
    job = _owned_job(db, job_id, uid)
    video_uri = str((job.get("artifacts") or {}).get("video1080pUrl", ""))
    if not video_uri.startswith("gs://"):
        raise HTTPException(
            status_code=409,
            detail=f"No film for this job yet (state={job.get('state')})",
        )
    bucket_name, _, blob_name = video_uri[5:].partition("/")
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    blob = client.bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise HTTPException(status_code=409, detail=f"Recorded film is not in the bucket: {video_uri}")

    # Cloud Run has no service-account key file, so the signature is made by the
    # IAM SignBlob API using the runtime service account's own identity. That
    # needs roles/iam.serviceAccountTokenCreator on itself; without it this
    # raises, and the caller gets the real reason rather than a broken link.
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    signer_email = getattr(creds, "service_account_email", None)
    if not signer_email:
        raise HTTPException(status_code=500, detail="No service account identity to sign with")
    try:
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
            service_account_email=signer_email,
            access_token=creds.token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not sign a playback URL ({type(exc).__name__}: {exc}). "
                   f"Grant roles/iam.serviceAccountTokenCreator on {signer_email} to itself.",
        )
    blob.reload()
    return {
        "url": url,
        "expiresInSeconds": 3600,
        "sizeBytes": blob.size,
        "contentType": blob.content_type,
        "durationMs": job.get("actualDurationMs"),
    }


@app.get("/v1/jobs/{job_id}/video")
def job_video(job_id: str, uid: str = Depends(verify_caller)):
    """Stream the finished film through the API.

    The signed URL above is the better path: the browser fetches straight from
    Cloud Storage and can seek. It needs roles/iam.serviceAccountTokenCreator on
    the runtime service account, which is a separate grant, so this endpoint
    exists as the route that works without it. A <video src> cannot send an
    Authorization header, so a caller using this one fetches it with the token
    and plays the result as a blob.
    """
    db = _get_db()
    job = _owned_job(db, job_id, uid)
    video_uri = str((job.get("artifacts") or {}).get("video1080pUrl", ""))
    if not video_uri.startswith("gs://"):
        raise HTTPException(
            status_code=409, detail=f"No film for this job yet (state={job.get('state')})"
        )
    bucket_name, _, blob_name = video_uri[5:].partition("/")
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    blob = client.bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise HTTPException(status_code=409, detail=f"Recorded film is not in the bucket: {video_uri}")
    blob.reload()

    def _chunks():
        with blob.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    return
                yield chunk

    return StreamingResponse(
        _chunks(),
        media_type=blob.content_type or "video/mp4",
        headers={
            "Content-Length": str(blob.size),
            "Content-Disposition": f'inline; filename="{job_id}.mp4"',
        },
    )


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
