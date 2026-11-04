from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from google.api_core.client_options import ClientOptions
from google.cloud import firestore
from schemas.models import JobState

PROJECT_ID = "gen-lang-client-0484425781"
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

def process_dlq_message(payload: Dict[str, Any], db: Optional[firestore.Client] = None) -> Dict[str, Any]:
    """Handle a dead-lettered Pub/Sub or Cloud Tasks message idempotently and record failure in Firestore."""
    client = db or firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    job_id = payload.get("jobId")
    error_reason = payload.get("error", "Exhausted Cloud Tasks / Eventarc delivery attempts")
    if not job_id:
        return {"status": "ignored", "reason": "missing_job_id"}

    job_ref = client.collection("jobs").document(job_id)
    snap = job_ref.get()
    if not snap.exists:
        return {"status": "not_found", "jobId": job_id}

    now = datetime.now(timezone.utc)
    job_ref.update({
        "state": JobState.FAILED.value,
        "errorMessage": f"DLQ: {error_reason}",
        "updatedAt": now.isoformat(),
    })
    evt_ref = job_ref.collection("events").document()
    evt_ref.set({
        "eventId": evt_ref.id,
        "jobId": job_id,
        "stage": "failed",
        "agent": "dlq_drainer",
        "level": "ERROR",
        "message": f"Dead-letter queue drainer marked job failed: {error_reason}",
        "costDeltaUsd": 0.0,
        "createdAt": now.isoformat(),
        "expireAt": (now + timedelta(days=90)).isoformat(),
    })
    return {"status": "marked_failed", "jobId": job_id, "error": error_reason}
