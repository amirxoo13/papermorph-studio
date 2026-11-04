import pytest
from datetime import datetime, timezone, timedelta
from google.api_core.client_options import ClientOptions
from google.cloud import firestore
from schemas.models import JobDoc, JobState, ContentFormat, LanguageCode
from papermorph_agents.budget import CostTracker, BudgetExceeded
from papermorph_agents.duration import evaluate_and_adjust_durations
from services.workflows.orchestrator import OrchestratorEngine
from services.reaper.src.main import reap_stuck_jobs
from services.dlq_drainer_shim import process_dlq_message

PROJECT_ID = "gen-lang-client-0484425781"
DB = firestore.Client(project=PROJECT_ID, client_options=ClientOptions(quota_project_id=PROJECT_ID))

def _create_job(job_id: str, **overrides) -> firestore.DocumentReference:
    doc = JobDoc(
        jobId=job_id,
        ownerUid="phase6-tester",
        title=f"Test {job_id}",
        format=ContentFormat.TEXTBOOK_LESSON,
        language=LanguageCode.EN,
        sourceUri="gs://gen-lang-client-0484425781-pm-raw-uploads/test.txt",
        **overrides,
    )
    ref = DB.collection("jobs").document(job_id)
    ref.set(doc.model_dump())
    return ref

def _cleanup_job(ref: firestore.DocumentReference):
    for sub in ["events", "scenes", "chunks"]:
        for s in ref.collection(sub).stream():
            s.reference.delete()
    ref.delete()

def test_scenario_1_human_in_the_loop_approval_pause_and_resume():
    ref = _create_job("p6-s1-approval", state=JobState.PLANNING, requireApproval=True)
    try:
        eng = OrchestratorEngine(db=DB)
        next_state = eng.handle_planning_complete("p6-s1-approval")
        assert next_state == JobState.AWAITING_APPROVAL
        assert ref.get().to_dict()["state"] == "awaiting_approval"
        resumed = eng.approve_job("p6-s1-approval", approver_uid="instructor-1")
        assert resumed["state"] == "scripting"
        assert resumed.get("approvedAt") is not None
    finally:
        _cleanup_job(ref)

def test_scenario_2_single_shard_transient_failure_retries_only_failed_shard():
    ref = _create_job("p6-s2-shard-retry", state=JobState.RENDERING)
    try:
        eng = OrchestratorEngine(db=DB)
        call_count = {"n": 0}
        def flaky_shard(idx: int):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("Transient FFmpeg worker preemption")
            return {"shardUri": f"gs://work/shard-{idx:03d}.mp4"}
        out = eng.execute_shard_with_retry("p6-s2-shard-retry", shard_index=4, shard_fn=flaky_shard)
        assert out["attempts"] == 3
        assert out["result"]["shardUri"].endswith("shard-004.mp4")
    finally:
        _cleanup_job(ref)

def test_scenario_3_critic_loop_rewrite_cap_prevents_infinite_loop():
    ref = _create_job("p6-s3-critic-cap", state=JobState.CRITIQUING, stageAttempts={"critiquing": 3})
    try:
        eng = OrchestratorEngine(db=DB)
        state = eng.evaluate_critic_loop("p6-s3-critic-cap", visual_score=0.72, pedagogy_score=0.91)
        assert state == JobState.PUBLISHING
    finally:
        _cleanup_job(ref)

def test_scenario_4_budget_exceeded_pauses_job_and_resumes_on_cap_increase():
    ref = _create_job("p6-s4-budget", state=JobState.ILLUSTRATING, costCapUsd=0.02)
    try:
        tracker = CostTracker(project_id=PROJECT_ID, db=DB)
        with pytest.raises(BudgetExceeded):
            tracker.record_usage("p6-s4-budget", stage="illustrating", agent_name="illustrator", model="imagen-3.0-generate-002", media_units=2)
        assert ref.get().to_dict()["state"] == "paused_budget"
        ref.update({"costCapUsd": 5.0})
        eng = OrchestratorEngine(db=DB)
        resumed = eng.transition_state("p6-s4-budget", JobState.ILLUSTRATING, "Cap raised to $5.00; resuming.")
        assert resumed["state"] == "illustrating"
    finally:
        _cleanup_job(ref)

def test_scenario_5_stuck_job_reaper_marks_stale_jobs_failed():
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    ref = _create_job("p6-s5-stuck", state=JobState.RENDERING, updatedAt=stale_time)
    try:
        reaped = reap_stuck_jobs(timeout_minutes=25, db=DB)
        reaped_ids = [r["jobId"] for r in reaped]
        assert "p6-s5-stuck" in reaped_ids
        assert ref.get().to_dict()["state"] == "failed"
    finally:
        _cleanup_job(ref)

def test_scenario_6_dlq_drainer_marks_poison_message_failed():
    ref = _create_job("p6-s6-dlq", state=JobState.INGESTING)
    try:
        res = process_dlq_message({"jobId": "p6-s6-dlq", "error": "Corrupt PDF header after 5 retries"}, db=DB)
        assert res["status"] == "marked_failed"
        assert ref.get().to_dict()["state"] == "failed"
    finally:
        _cleanup_job(ref)

def test_scenario_7_duration_drift_auto_scaled_into_tolerance_window():
    res = evaluate_and_adjust_durations([45000, 45000, 45000, 45000, 45000, 45000], target_total_ms=300000)
    assert res.withinWindow is True
    assert res.totalDurationMs == 300000
    assert res.action == "scale_pauses"

def test_scenario_8_user_cancellation_terminates_active_job():
    ref = _create_job("p6-s8-cancel", state=JobState.SCRIPTING)
    try:
        eng = OrchestratorEngine(db=DB)
        cancelled = eng.transition_state("p6-s8-cancel", JobState.CANCELLED, "Cancelled by user request")
        assert cancelled["state"] == "cancelled"
    finally:
        _cleanup_job(ref)
