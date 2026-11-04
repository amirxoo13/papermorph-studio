import pytest
from google.cloud import firestore
from schemas.models import JobDoc, ContentFormat, LanguageCode
from papermorph_agents.agent import AGENT_REGISTRY, AGENT_SPECS, root_agent, run_live_planning_pipeline
from papermorph_agents.budget import CostTracker, BudgetExceeded, compute_llm_cost
from papermorph_agents.duration import evaluate_and_adjust_durations, TARGET_TOTAL_MS

PROJECT_ID = "gen-lang-client-0484425781"

def test_all_23_agents_registered():
    assert len(AGENT_SPECS) == 23
    assert len(AGENT_REGISTRY) == 23
    assert len(root_agent.sub_agents) == 23
    expected_names = {
        "router", "ingestor", "curriculum_planner", "narrative_director",
        "character_bible", "scene_scriptwriter", "farsi_localizer", "fact_grounder",
        "voice_director", "forced_aligner", "duration_controller", "illustrator",
        "svg_diagrammer", "motion_choreographer", "broll_director", "sound_designer",
        "render_dispatcher", "shorts_cutter", "visual_critic", "pedagogy_critic",
        "accessibility_auditor", "scorm_packager", "publisher"
    }
    assert set(AGENT_REGISTRY.keys()) == expected_names

def test_duration_controller_within_window():
    # Exactly 300,000ms across 6 scenes
    res = evaluate_and_adjust_durations([50000] * 6)
    assert res.withinWindow is True
    assert res.action == "pass"
    assert res.totalDurationMs == 300000

def test_duration_controller_scales_pauses():
    # 270,000ms (-10% deviation, within 15% scaling band)
    res = evaluate_and_adjust_durations([45000] * 6)
    assert res.withinWindow is True
    assert res.action == "scale_pauses"
    assert res.totalDurationMs == TARGET_TOTAL_MS
    assert sum(res.adjustedSceneDurationsMs) == TARGET_TOTAL_MS

def test_duration_controller_flags_extreme_deviation():
    # 120,000ms (-60% deviation)
    res = evaluate_and_adjust_durations([20000] * 6)
    assert res.withinWindow is False
    assert res.action == "split_or_expand"
    assert sum(res.adjustedSceneDurationsMs) == TARGET_TOTAL_MS

def test_budget_tracker_enforces_hard_cap():
    db = firestore.Client(project=PROJECT_ID)
    job_id = "phase3-budget-cap-test"
    job_ref = db.collection("jobs").document(job_id)
    job = JobDoc(
        jobId=job_id,
        ownerUid="test-user",
        title="Budget Cap Test",
        format=ContentFormat.TEXTBOOK_LESSON,
        language=LanguageCode.EN,
        sourceUri="gs://gen-lang-client-0484425781-pm-raw-uploads/sample.txt",
        costCapUsd=0.005,  # Very low cap ($0.005)
    )
    job_ref.set(job.model_dump())
    tracker = CostTracker(project_id=PROJECT_ID, db=db)

    try:
        # First small Flash call fits under $0.005
        c1 = tracker.record_usage(job_id, "ingesting", "ingestor", "gemini-2.5-flash", tokens_in=500, tokens_out=200)
        assert c1 > 0

        # Second Pro call exceeds $0.005 -> raises BudgetExceeded & transitions job to paused_budget
        with pytest.raises(BudgetExceeded):
            tracker.record_usage(job_id, "planning", "curriculum_planner", "gemini-2.5-pro", tokens_in=2000, tokens_out=1000)

        snap = job_ref.get().to_dict()
        assert snap["state"] == "paused_budget"
        assert "Budget cap" in snap["errorMessage"]
    finally:
        for evt in job_ref.collection("events").stream():
            evt.reference.delete()
        job_ref.delete()
