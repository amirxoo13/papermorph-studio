"""Unit tests that need no cloud credentials.

The tests they replace (test_phase7.py, test_phase8.py) asserted the old
behaviour: they set an `X-Firebase-Uid` header themselves and checked that the
request was accepted, which only proved that the API trusted the header. With
real token verification there is nothing a test can assert about identity
without minting a real Identity Platform token, so that check moved to
reports/VERIFY.md as a live command.

What is left here is the logic that is worth testing in isolation: the mapping
from a job document to the render job's environment, and the cost table's
refusal to price a model it has no verified price for.
"""

from __future__ import annotations

import pytest

from services.api.src.dispatch import (
    DispatchNotConfigured,
    FORMAT_TO_TIER,
    _slugify,
    render_job_env,
)
from services.common.budget import (
    MODEL_PRICING_USD,
    PRICE_NOT_YET_VERIFIED,
    UnknownModelPricing,
    compute_llm_cost,
    compute_media_cost,
)
from services.common.duration import evaluate_and_adjust_durations


def test_slug_is_engine_safe():
    assert _slugify("Zahhak and Kaveh!", "job-abcdef123456") == "zahhak-and-kaveh"
    assert _slugify("  ", "job-abcdef123456") == "job-ef123456"
    assert _slugify("ضحاک", "job-abcdef123456") == "job-ef123456"


def test_every_content_format_maps_to_an_engine_tier():
    # new_book.py accepts exactly these four tier names.
    assert set(FORMAT_TO_TIER.values()) <= {"lesson", "picture", "documentary", "shorts"}


def test_render_job_env_carries_what_entrypoint_requires():
    job = {
        "jobId": "job-abcdef123456",
        "title": "Zahhak",
        "format": "documentary",
        "language": "fa",
        "targetDurationMs": 600_000,
        "costCapUsd": 7.5,
        "brief": "a real brief",
    }
    env = render_job_env(job, "once upon a time")
    # entrypoint.sh exits non-zero without each of these four.
    for required in ("BOOK_SLUG", "BOOK_TITLE", "STORY_TEXT", "TARGET_SECONDS"):
        assert env[required], f"{required} must be set"
    assert env["TARGET_SECONDS"] == "600"
    assert env["TIER"] == "documentary"
    assert env["STORY_TEXT"] == "once upon a time"


def test_non_picture_tier_without_a_brief_is_refused():
    job = {"jobId": "job-1", "title": "T", "format": "documentary", "targetDurationMs": 300_000}
    with pytest.raises(DispatchNotConfigured):
        render_job_env(job, "text")


def test_picture_tier_needs_no_brief():
    job = {"jobId": "job-1", "title": "T", "format": "picture_book", "targetDurationMs": 300_000}
    assert render_job_env(job, "text")["TIER"] == "picture"


def test_retired_models_are_not_priced():
    for retired in ("gemini-2.5-pro", "gemini-2.5-flash", "imagen-3.0-generate-002"):
        assert retired not in MODEL_PRICING_USD


def test_unverified_price_raises_instead_of_guessing():
    for model in PRICE_NOT_YET_VERIFIED:
        with pytest.raises(UnknownModelPricing):
            compute_llm_cost(model, 1000, 1000)
    with pytest.raises(UnknownModelPricing):
        compute_media_cost("gemini-nano-banana-2.1", 1)


def test_zero_usage_costs_nothing_without_a_price():
    assert compute_llm_cost("gemini-4-argon", 0, 0) == 0.0
    assert compute_media_cost("gemini-4-argon", 0) == 0.0


def test_verified_price_is_used():
    # 1000 in + 1000 out at $0.00075 / $0.00375 per 1k.
    assert compute_llm_cost("gemini-3.8-flash", 1000, 1000) == pytest.approx(0.0045)


def test_duration_adjustment_hits_the_target():
    res = evaluate_and_adjust_durations([50_000] * 6, target_total_ms=300_000)
    assert res.withinWindow
    assert sum(res.adjustedSceneDurationsMs) == pytest.approx(300_000, rel=0.08)


def test_unknown_format_is_refused_not_defaulted():
    # It used to fall back to "documentary" for any unrecognised format, so a
    # typo silently produced the wrong tier.
    job = {"jobId": "job-1", "title": "T", "format": "nonsense", "targetDurationMs": 300_000}
    with pytest.raises(DispatchNotConfigured):
        render_job_env(job, "text")


def test_legacy_documentary_shorts_still_maps():
    job = {
        "jobId": "job-1", "title": "T", "format": "documentary_shorts",
        "targetDurationMs": 300_000, "brief": "b",
    }
    assert render_job_env(job, "text")["TIER"] == "documentary"


def test_shorts_tier_is_reachable():
    job = {
        "jobId": "job-1", "title": "T", "format": "short",
        "targetDurationMs": 150_000, "brief": "b",
    }
    assert render_job_env(job, "text")["TIER"] == "shorts"
