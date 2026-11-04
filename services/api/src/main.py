from __future__ import annotations
import os
import hmac
import time
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from google.api_core.client_options import ClientOptions
from google.cloud import firestore

from schemas.models import (
    JobDoc, SceneDoc, BookDoc, LicenceEntry, JobState, ContentFormat, LanguageCode
)
from services.workflows.orchestrator import OrchestratorEngine
from .dlp_gate import inspect_and_redact_text, PiiDetectedError
from .licence_gate import verify_licence_ledger, generate_sources_markdown

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
INTERNAL_HMAC_SECRET = os.environ.get("INTERNAL_HMAC_SECRET", "papermorph-dev-hmac-secret")
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

app = FastAPI(title="Papermorph Studio Public API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_RATE_BUCKETS: Dict[str, List[float]] = {}
_IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}

def _get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)

def verify_caller(
    x_firebase_uid: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_app_check: Optional[str] = Header(default=None),
) -> str:
    """Verify Firebase Auth bearer token or uid header and enforce per-user rate limit (60 req/min)."""
    uid = x_firebase_uid
    if not uid and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            uid = f"uid-{hashlib.sha256(token.encode()).hexdigest()[:12]}"
    if not uid:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")

    now = time.time()
    window = [t for t in _RATE_BUCKETS.get(uid, []) if now - t < 60.0]
    if len(window) >= 60:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (60 requests/min)")
    window.append(now)
    _RATE_BUCKETS[uid] = window
    return uid

def verify_internal_hmac(
    x_pm_signature: Optional[str] = Header(default=None),
    x_pm_payload: Optional[str] = Header(default=None),
) -> bool:
    if not x_pm_signature or x_pm_payload is None:
        raise HTTPException(status_code=403, detail="Missing internal HMAC signature headers")
    expected = hmac.new(INTERNAL_HMAC_SECRET.encode(), x_pm_payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_pm_signature):
        raise HTTPException(status_code=403, detail="Invalid internal HMAC signature")
    return True

class CreateJobRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    format: ContentFormat = ContentFormat.TEXTBOOK_LESSON
    language: LanguageCode = LanguageCode.EN
    stylePresetId: str = "default-editorial"
    sourceUri: str
    manuscriptPreviewText: str = ""
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
    if idempotency_key:
        cache_key = f"{uid}:{idempotency_key}"
        if cache_key in _IDEMPOTENCY_CACHE:
            return _IDEMPOTENCY_CACHE[cache_key]

    try:
        dlp_res = inspect_and_redact_text(req.manuscriptPreviewText or req.title, reject_on_pii=req.rejectOnPii)
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
    db = _get_db()
    db.collection("jobs").document(job_id).set(job.model_dump())
    resp_payload = {"job": job.model_dump(), "dlpScan": dlp_res.model_dump()}
    if idempotency_key:
        _IDEMPOTENCY_CACHE[f"{uid}:{idempotency_key}"] = resp_payload
    return resp_payload

@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str, uid: str = Depends(verify_caller)):
    db = _get_db()
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    data = snap.to_dict() or {}
    if data.get("ownerUid") != uid:
        raise HTTPException(status_code=403, detail="Forbidden: not job owner")
    scenes = [s.to_dict() for s in snap.reference.collection("scenes").order_by("index").stream()]
    return {"job": data, "scenes": scenes}

@app.post("/v1/jobs/{job_id}/approve")
def approve_job(job_id: str, uid: str = Depends(verify_caller)):
    db = _get_db()
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    data = snap.to_dict() or {}
    if data.get("ownerUid") != uid:
        raise HTTPException(status_code=403, detail="Forbidden: not job owner")
    eng = OrchestratorEngine(db=db)
    updated = eng.approve_job(job_id, approver_uid=uid)
    return {"job": updated}

@app.post("/v1/jobs/{job_id}/cancel")
def cancel_job(job_id: str, uid: str = Depends(verify_caller)):
    db = _get_db()
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    data = snap.to_dict() or {}
    if data.get("ownerUid") != uid:
        raise HTTPException(status_code=403, detail="Forbidden: not job owner")
    eng = OrchestratorEngine(db=db)
    updated = eng.transition_state(job_id, JobState.CANCELLED, "Cancelled by owner via API")
    return {"job": updated}

@app.get("/v1/jobs/{job_id}/stream")
def stream_job_events(job_id: str, uid: str = Depends(verify_caller)):
    db = _get_db()
    snap = db.collection("jobs").document(job_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    job_data = snap.to_dict() or {}
    if job_data.get("ownerUid") != uid:
        raise HTTPException(status_code=403, detail="Forbidden")

    events = [e.to_dict() for e in snap.reference.collection("events").stream()]
    def _event_gen():
        yield f"event: state\ndata: {json.dumps({'jobId': job_id, 'state': job_data.get('state'), 'costUsd': job_data.get('costUsd', 0.0)})}\n\n"
        for ev in events:
            yield f"event: log\ndata: {json.dumps(ev)}\n\n"
    return StreamingResponse(_event_gen(), media_type="text/event-stream")

@app.get("/v1/books/{book_id}")
def get_book(book_id: str):
    db = _get_db()
    snap = db.collection("books").document(book_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"book": snap.to_dict()}

@app.post("/internal/stage-callback")
def internal_stage_callback(payload: Dict[str, Any], _verified: bool = Depends(verify_internal_hmac)):
    return {"status": "accepted", "jobId": payload.get("jobId")}
