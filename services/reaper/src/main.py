from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from google.api_core.client_options import ClientOptions
from google.cloud import firestore
from schemas.models import JobState

PROJECT_ID = "gen-lang-client-0484425781"
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)
ACTIVE_STATES = {
    JobState.INGESTING.value,
    JobState.PLANNING.value,
    JobState.SCRIPTING.value,
    JobState.SYNTHESIZING_VOICE.value,
    JobState.ILLUSTRATING.value,
    JobState.RENDERING.value,
    JobState.CRITIQUING.value,
    JobState.PUBLISHING.value,
}

def reap_stuck_jobs(timeout_minutes: int = 25, db: Optional[firestore.Client] = None) -> List[Dict[str, Any]]:
    """Find jobs in active non-terminal states with `updatedAt` older than `timeout_minutes` and mark them `failed`."""
    client = db or firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
    reaped = []
    for snap in client.collection("jobs").stream():
        data = snap.to_dict() or {}
        state = data.get("state")
        if state not in ACTIVE_STATES:
            continue
        updated_raw = data.get("updatedAt")
        if not updated_raw:
            continue
        try:
            updated_dt = datetime.fromisoformat(updated_raw)
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if updated_dt < cutoff:
            now_iso = datetime.now(timezone.utc).isoformat()
            msg = f"Reaped stuck job in state '{state}' (last heartbeat {updated_raw} > {timeout_minutes}m ago)"
            snap.reference.update({
                "state": JobState.FAILED.value,
                "errorMessage": msg,
                "updatedAt": now_iso,
            })
            reaped.append({"jobId": snap.id, "previousState": state, "reason": msg})
    return reaped
