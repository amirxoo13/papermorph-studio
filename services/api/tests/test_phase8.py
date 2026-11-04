import hmac
import hashlib
from fastapi.testclient import TestClient
from google.api_core.client_options import ClientOptions
from google.cloud import firestore
from schemas.models import JobState
from services.workflows.orchestrator import OrchestratorEngine
from src.main import app, INTERNAL_HMAC_SECRET

PROJECT_ID = "gen-lang-client-0484425781"
DB = firestore.Client(project=PROJECT_ID, client_options=ClientOptions(quota_project_id=PROJECT_ID))
client = TestClient(app)

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["service"] == "pm-api"

def test_create_get_approve_stream_and_cancel_job_lifecycle():
    headers = {"X-Firebase-Uid": "api-test-user", "Idempotency-Key": "idem-key-001"}
    payload = {
        "title": "Quantum Mechanics Intro",
        "format": "textbook_lesson",
        "language": "en",
        "sourceUri": "gs://gen-lang-client-0484425781-pm-raw-uploads/qm.txt",
        "manuscriptPreviewText": "Wave-particle duality and Schrodinger equation overview.",
        "requireApproval": True,
    }
    r1 = client.post("/v1/jobs", json=payload, headers=headers)
    assert r1.status_code == 200
    job_id = r1.json()["job"]["jobId"]

    # Verify idempotency key returns identical jobId
    r2 = client.post("/v1/jobs", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["job"]["jobId"] == job_id

    try:
        # Transition job to awaiting_approval so we can test /approve
        eng = OrchestratorEngine(db=DB)
        eng.transition_state(job_id, JobState.INGESTING)
        eng.transition_state(job_id, JobState.PLANNING)
        eng.handle_planning_complete(job_id)

        r_get = client.get(f"/v1/jobs/{job_id}", headers=headers)
        assert r_get.status_code == 200
        assert r_get.json()["job"]["state"] == "awaiting_approval"

        r_app = client.post(f"/v1/jobs/{job_id}/approve", headers=headers)
        assert r_app.status_code == 200
        assert r_app.json()["job"]["state"] == "scripting"

        r_sse = client.get(f"/v1/jobs/{job_id}/stream", headers=headers)
        assert r_sse.status_code == 200
        assert "event: state" in r_sse.text

        r_cancel = client.post(f"/v1/jobs/{job_id}/cancel", headers=headers)
        assert r_cancel.status_code == 200
        assert r_cancel.json()["job"]["state"] == "cancelled"
    finally:
        ref = DB.collection("jobs").document(job_id)
        for e in ref.collection("events").stream():
            e.reference.delete()
        ref.delete()

def test_hmac_internal_callback_protection():
    body_str = '{"jobId":"job-123"}'
    sig = hmac.new(INTERNAL_HMAC_SECRET.encode(), body_str.encode(), hashlib.sha256).hexdigest()
    r_ok = client.post(
        "/internal/stage-callback",
        json={"jobId": "job-123"},
        headers={"X-Pm-Signature": sig, "X-Pm-Payload": body_str},
    )
    assert r_ok.status_code == 200

    r_bad = client.post(
        "/internal/stage-callback",
        json={"jobId": "job-123"},
        headers={"X-Pm-Signature": "invalid-sig", "X-Pm-Payload": body_str},
    )
    assert r_bad.status_code == 403
