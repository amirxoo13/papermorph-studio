from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:  # the SDK is only needed by CostTracker, not by compute_*
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

class UnknownModelPricing(RuntimeError):
    """Raised when a cost is requested for a model with no verified price.

    Returning a guess, or falling back to another model's price, is how a run
    reports a plausible cost for work it did not do. The earlier table priced
    every unknown model as a retired cheap Flash model and priced unknown media
    at zero, so a job could report a few hundredths of a dollar for a film that
    never rendered. An unknown model must stop the run instead.
    """

    def __init__(self, model: str):
        self.model = model
        super().__init__(
            f"No verified price for model '{model}'. Read the real figure from Cloud Billing "
            f"and add it to MODEL_PRICING_USD with its source, or record this usage with "
            f"media_units/tokens of 0 and track the cost from Billing only."
        )


# Unit pricing (USD). Only prices taken from a primary source belong here, and
# each one names that source. The models in use are listed in CLAUDE.md §3;
# the retired ones that used to fill this table (gemini-2.5-*, imagen-*) are
# gone, and nothing falls back to them.
#
# CLAUDE.md §3: "Billing is the only authority here; never reason from SKU names
# or pricing pages." So this table is a convenience for in-run cap enforcement,
# never the authority for what a run cost. Reconcile against Cloud Billing.
MODEL_PRICING_USD = {
    # Google's own announcement of Gemini 3.8 Flash: $0.75 per 1M input tokens
    # and $3.75 per 1M output tokens as an introductory price, expiring
    # 2026-12-31, after which $1.50 / $7.50 apply.
    # https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/
    "gemini-3.8-flash": {"input_per_1k": 0.00075, "output_per_1k": 0.00375},
}

# Models known to be in use whose price has not been read from Billing yet.
# Listed so the error says "not verified" rather than "unknown model", and so
# nobody re-adds a guessed number for them.
PRICE_NOT_YET_VERIFIED = (
    "gemini-4-argon",
    "gemini-nano-banana-2.1",
    "gemini-3-pro-image",
    "gemini-3.1-flash-image",
    "gemini-3.8-flash-tts",
    "veo-3.1-generate-001",
    "veo-3.1-fast-generate-001",
)

def compute_llm_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Token cost for a model with a verified price. Raises for anything else."""
    if tokens_in == 0 and tokens_out == 0:
        return 0.0
    pricing = MODEL_PRICING_USD.get(model)
    if pricing is None or "input_per_1k" not in pricing:
        raise UnknownModelPricing(model)
    cost = (tokens_in / 1000.0) * pricing["input_per_1k"] + (tokens_out / 1000.0) * pricing[
        "output_per_1k"
    ]
    return round(cost, 6)


def compute_media_cost(model: str, units: float) -> float:
    """Per-image, per-character or per-minute cost. Raises for anything else."""
    if units == 0:
        return 0.0
    pricing = MODEL_PRICING_USD.get(model)
    if pricing is None:
        raise UnknownModelPricing(model)
    if "per_image" in pricing:
        return round(units * pricing["per_image"], 6)
    if "per_1k_chars" in pricing:
        return round((units / 1000.0) * pricing["per_1k_chars"], 6)
    if "per_minute_audio" in pricing:
        return round(units * pricing["per_minute_audio"], 6)
    raise UnknownModelPricing(model)

class CostTracker:
    def __init__(self, project_id: str = "gen-lang-client-0484425781", db: Optional["firestore.Client"] = None):
        from google.cloud import firestore as _firestore

        self.project_id = project_id
        self.db = db or _firestore.Client(project=project_id)

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
