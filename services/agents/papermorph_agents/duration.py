from __future__ import annotations
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field

TARGET_TOTAL_MS = 300_000
TOLERANCE_RATIO = 0.08  # +/- 8% (276,000ms .. 324,000ms)
MIN_TOTAL_MS = int(TARGET_TOTAL_MS * (1.0 - TOLERANCE_RATIO))
MAX_TOTAL_MS = int(TARGET_TOTAL_MS * (1.0 + TOLERANCE_RATIO))

class DurationCheckResult(BaseModel):
    withinWindow: bool
    totalDurationMs: int
    targetDurationMs: int = TARGET_TOTAL_MS
    deviationRatio: float
    action: str  # "pass" | "scale_pauses" | "split_or_expand" | "trim_or_merge"
    adjustedSceneDurationsMs: List[int] = Field(default_factory=list)

def evaluate_and_adjust_durations(
    scene_durations_ms: List[int],
    target_total_ms: int = TARGET_TOTAL_MS,
    tolerance_ratio: float = TOLERANCE_RATIO,
) -> DurationCheckResult:
    """Deterministic duration controller enforcing target_total_ms +/- 8%."""
    if not scene_durations_ms:
        return DurationCheckResult(
            withinWindow=False,
            totalDurationMs=0,
            targetDurationMs=target_total_ms,
            deviationRatio=-1.0,
            action="split_or_expand",
            adjustedSceneDurationsMs=[],
        )

    total_ms = sum(scene_durations_ms)
    deviation = (total_ms - target_total_ms) / float(target_total_ms)
    min_ms = int(target_total_ms * (1.0 - tolerance_ratio))
    max_ms = int(target_total_ms * (1.0 + tolerance_ratio))

    if min_ms <= total_ms <= max_ms:
        return DurationCheckResult(
            withinWindow=True,
            totalDurationMs=total_ms,
            targetDurationMs=target_total_ms,
            deviationRatio=round(deviation, 4),
            action="pass",
            adjustedSceneDurationsMs=list(scene_durations_ms),
        )

    # If within +/- 15%, deterministically scale scene durations (pauses/padding) to hit target_total_ms
    if abs(deviation) <= 0.15 and total_ms > 0:
        scale = target_total_ms / float(total_ms)
        scaled = [max(1000, int(round(d * scale))) for d in scene_durations_ms]
        diff = target_total_ms - sum(scaled)
        scaled[-1] += diff
        return DurationCheckResult(
            withinWindow=True,
            totalDurationMs=sum(scaled),
            targetDurationMs=target_total_ms,
            deviationRatio=0.0,
            action="scale_pauses",
            adjustedSceneDurationsMs=scaled,
        )

    action = "split_or_expand" if total_ms < min_ms else "trim_or_merge"
    scale = target_total_ms / float(max(total_ms, 1))
    recommended = [max(1000, int(round(d * scale))) for d in scene_durations_ms]
    diff = target_total_ms - sum(recommended)
    recommended[-1] += diff
    return DurationCheckResult(
        withinWindow=False,
        totalDurationMs=total_ms,
        targetDurationMs=target_total_ms,
        deviationRatio=round(deviation, 4),
        action=action,
        adjustedSceneDurationsMs=recommended,
    )
