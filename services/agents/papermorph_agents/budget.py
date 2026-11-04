from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from google.cloud import firestore

class BudgetExceeded(RuntimeError):
    """Raised when a job's cumulative costUsd exceeds its costCapUsd."""
    def __init__(self, job_id: str, current_cost: float, cap_cost: float, attempted_delta: float):
        self.job_id = job_id
        self.current_cost = current_cost
        self.cap_cost = cap_cost
        self.attempted_delta = attempted_delta
        super().__init__(
            f"BudgetExceeded for job {job_id}: current=${current_cost:.4f} + delta=${attempted_delta:.4f} > cap=${cap_cost:.4f}"
        )

# Pinned unit pricing table (USD)
MODEL_PRICING_USD = {
    "gemini-3.5-pro": {"input_per_1k": 0.00125, "output_per_1k": 0.0100},
    "gemini-3-pro-preview": {"input_per_1k": 0.00125, "output_per_1k": 0.0100},
    "gemini-3.5-flash": {"input_per_1k": 0.00015, "output_per_1k": 0.00060},
    "gemini-2.5-pro": {"input_per_1k": 0.00125, "output_per_1k": 0.0100},
    "gemini-2.5-flash": {"input_per_1k": 0.00015, "output_per_1k": 0.00060},
    "imagen-3.0-generate-002": {"per_image": 0.0400},
    "en-US-Chirp3-HD-Achernar": {"per_1k_chars": 0.0300},
    "fa-IR-Standard-A": {"per_1k_chars": 0.0040},
    "chirp_2": {"per_minute_audio": 0.0160},
}

def compute_llm_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = MODEL_PRICING_USD.get(model, MODEL_PRICING_USD["gemini-2.5-flash"])
    cost = (tokens_in / 1000.0) * pricing.get("input_per_1k", 0.00015) + (
        tokens_out / 1000.0
    ) * pricing.get("output_per_1k", 0.00060)
    return round(cost, 6)

def compute_media_cost(model: str, units: float) -> float:
    pricing = MODEL_PRICING_USD.get(model, {})
    if "per_image" in pricing:
        return round(units * pricing["per_image"], 6)
    if "per_1k_chars" in pricing:
        return round((units / 1000.0) * pricing["per_1k_chars"], 6)
    if "per_minute_audio" in pricing:
        return round(units * pricing["per_minute_audio"], 6)
    return 0.0

class CostTracker:
    def __init__(self, project_id: str = "gen-lang-client-0484425781", db: Optional[firestore.Client] = None):
        self.project_id = project_id
        self.db = db or firestore.Client(project=project_id)

    def record_usage(
        self,
        job_id: str,
        stage: str,
        agent_name: str,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        media_units: float = 0.0,
        trace_id: Optional[str] = None,
    ) -> float:
        delta_usd = compute_llm_cost(model, tokens_in, tokens_out) + compute_media_cost(model, media_units)
        job_ref = self.db.collection("jobs").document(job_id)
        snap = job_ref.get()
        if not snap.exists:
            raise ValueError(f"Job {job_id} not found in Firestore")

        data = snap.to_dict() or {}
        current_cost = float(data.get("costUsd", 0.0))
        cost_cap = float(data.get("costCapUsd", 5.0))
        new_cost = round(current_cost + delta_usd, 6)
        now_iso = datetime.now(timezone.utc).isoformat()
        expire_iso = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()

        if new_cost > cost_cap:
            # Transition job state to paused_budget atomically
            job_ref.update({
                "state": "paused_budget",
                "errorMessage": f"Budget cap ${cost_cap:.2f} exceeded at stage {stage} (agent {agent_name}): attempted ${new_cost:.4f}",
                "updatedAt": now_iso,
            })
            evt_ref = job_ref.collection("events").document()
            evt_ref.set({
                "eventId": evt_ref.id,
                "jobId": job_id,
                "stage": stage,
                "agent": agent_name,
                "level": "WARN",
                "message": f"BudgetExceeded: ${new_cost:.4f} > cap ${cost_cap:.4f}. Job paused.",
                "costDeltaUsd": 0.0,
                "traceId": trace_id,
                "createdAt": now_iso,
                "expireAt": expire_iso,
            })
            raise BudgetExceeded(job_id, current_cost, cost_cap, delta_usd)

        job_ref.update({
            "costUsd": new_cost,
            "tokensIn": int(data.get("tokensIn", 0)) + tokens_in,
            "tokensOut": int(data.get("tokensOut", 0)) + tokens_out,
            "updatedAt": now_iso,
        })
        evt_ref = job_ref.collection("events").document()
        evt_ref.set({
            "eventId": evt_ref.id,
            "jobId": job_id,
            "stage": stage,
            "agent": agent_name,
            "level": "INFO",
            "message": f"Usage recorded for {model}: +{tokens_in}in/{tokens_out}out (+${delta_usd:.5f}, total=${new_cost:.4f})",
            "costDeltaUsd": delta_usd,
            "traceId": trace_id,
            "createdAt": now_iso,
            "expireAt": expire_iso,
        })
        return new_cost
