from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from google.api_core.client_options import ClientOptions
from google.cloud import firestore
from schemas.models import JobState, validate_transition
from services.common.budget import BudgetExceeded

PROJECT_ID = "gen-lang-client-0484425781"
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

MAX_STAGE_RETRIES = 3
MAX_CRITIC_REWRITES = 2
STUCK_JOB_TIMEOUT_MINUTES = 25

class OrchestratorEngine:
    """Coordinates job state transitions, idempotency, retries, human-in-the-loop pause/resume, and failure recovery."""

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)

    def transition_state(self, job_id: str, target_state: JobState, message: str = "", agent: str = "orchestrator") -> Dict[str, Any]:
        job_ref = self.db.collection("jobs").document(job_id)
        snap = job_ref.get()
        if not snap.exists:
            raise ValueError(f"Job {job_id} does not exist")
        data = snap.to_dict() or {}
        current_state = JobState(data.get("state", JobState.QUEUED.value))
        if current_state != target_state:
            validate_transition(current_state, target_state)
        now = datetime.now(timezone.utc)
        attempts = dict(data.get("stageAttempts", {}))
        attempts[target_state.value] = attempts.get(target_state.value, 0) + 1
        updates = {
            "state": target_state.value,
            "stageAttempts": attempts,
            "updatedAt": now.isoformat(),
        }
        if target_state == JobState.FAILED and message:
            updates["errorMessage"] = message
        job_ref.update(updates)
        evt_ref = job_ref.collection("events").document()
        evt_ref.set({
            "eventId": evt_ref.id,
            "jobId": job_id,
            "stage": target_state.value,
            "agent": agent,
            "level": "ERROR" if target_state == JobState.FAILED else "INFO",
            "message": message or f"State transitioned {current_state.value} -> {target_state.value}",
            "costDeltaUsd": 0.0,
            "createdAt": now.isoformat(),
            "expireAt": (now + timedelta(days=90)).isoformat(),
        })
        data.update(updates)
        return data

    def handle_planning_complete(self, job_id: str) -> JobState:
        """Scenario 1: Human-in-the-loop pause at `awaiting_approval` when `requireApproval=True`."""
        snap = self.db.collection("jobs").document(job_id).get()
        data = snap.to_dict() or {}
        if data.get("requireApproval", True) and not data.get("approvedAt"):
            self.transition_state(job_id, JobState.AWAITING_APPROVAL, "Paused awaiting human storyboard approval.")
            return JobState.AWAITING_APPROVAL
        self.transition_state(job_id, JobState.SCRIPTING, "Auto-approved storyboard; advancing to scripting.")
        return JobState.SCRIPTING

    def approve_job(self, job_id: str, approver_uid: str) -> Dict[str, Any]:
        """Resume a job from `awaiting_approval` -> `scripting`."""
        job_ref = self.db.collection("jobs").document(job_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        job_ref.update({"approvedAt": now_iso, "updatedAt": now_iso})
        return self.transition_state(job_id, JobState.SCRIPTING, f"Approved by {approver_uid}; resuming pipeline.")

    def execute_shard_with_retry(self, job_id: str, shard_index: int, shard_fn: Callable[[int], Dict[str, Any]], max_retries: int = MAX_STAGE_RETRIES) -> Dict[str, Any]:
        """Scenario 2: Single render shard failure retries only the failed shard up to `max_retries` times."""
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                res = shard_fn(shard_index)
                return {"shardIndex": shard_index, "attempts": attempt, "result": res}
            except Exception as e:
                last_err = str(e)
        self.transition_state(job_id, JobState.FAILED, f"Shard {shard_index} failed after {max_retries} attempts: {last_err}")
        raise RuntimeError(f"Shard {shard_index} exhausted retries: {last_err}")

    def evaluate_critic_loop(self, job_id: str, visual_score: float, pedagogy_score: float, threshold: float = 0.85) -> JobState:
        """Scenario 3: Critic loop capped at `MAX_CRITIC_REWRITES` (2) before advancing or failing gracefully."""
        snap = self.db.collection("jobs").document(job_id).get()
        data = snap.to_dict() or {}
        attempts = data.get("stageAttempts", {}).get(JobState.CRITIQUING.value, 0)
        if visual_score >= threshold and pedagogy_score >= threshold:
            self.transition_state(job_id, JobState.PUBLISHING, f"Critics passed (visual={visual_score}, pedagogy={pedagogy_score}).")
            return JobState.PUBLISHING
        if attempts <= MAX_CRITIC_REWRITES:
            target = JobState.ILLUSTRATING if visual_score < threshold else JobState.SCRIPTING
            self.transition_state(job_id, target, f"Critic requested targeted rewrite #{attempts} -> {target.value}.")
            return target
        # Cap reached: advance to publishing with warning event rather than infinite loop
        self.transition_state(job_id, JobState.PUBLISHING, f"Critic rewrite cap ({MAX_CRITIC_REWRITES}) reached; proceeding to publishing with audit note.")
        return JobState.PUBLISHING
