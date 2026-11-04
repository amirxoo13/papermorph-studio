import pytest
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from schemas.models import (
    JobDoc, SceneDoc, EventDoc, BookDoc, LicenceEntry,
    JobState, ContentFormat, LanguageCode,
    validate_transition, InvalidStateTransitionError
)

PROJECT_ID = "gen-lang-client-0484425781"

def test_valid_state_transitions():
    assert validate_transition(JobState.QUEUED, JobState.INGESTING)
    assert validate_transition(JobState.INGESTING, JobState.PLANNING)
    assert validate_transition(JobState.PLANNING, JobState.AWAITING_APPROVAL)
    assert validate_transition(JobState.AWAITING_APPROVAL, JobState.SCRIPTING)
    assert validate_transition(JobState.SCRIPTING, JobState.SYNTHESIZING_VOICE)
    assert validate_transition(JobState.SYNTHESIZING_VOICE, JobState.ILLUSTRATING)
    assert validate_transition(JobState.ILLUSTRATING, JobState.RENDERING)
    assert validate_transition(JobState.RENDERING, JobState.CRITIQUING)
    assert validate_transition(JobState.CRITIQUING, JobState.PUBLISHING)
    assert validate_transition(JobState.PUBLISHING, JobState.DONE)
    assert validate_transition(JobState.RENDERING, JobState.PAUSED_BUDGET)
    assert validate_transition(JobState.PAUSED_BUDGET, JobState.RENDERING)

def test_invalid_state_transitions():
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(JobState.QUEUED, JobState.DONE)
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(JobState.DONE, JobState.RENDERING)
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(JobState.CANCELLED, JobState.SCRIPTING)

def test_pydantic_schema_validation():
    job = JobDoc(
        jobId="job-test-001",
        ownerUid="user-123",
        title="Photosynthesis Textbook Lesson",
        format=ContentFormat.TEXTBOOK_LESSON,
        language=LanguageCode.EN,
        sourceUri="gs://gen-lang-client-0484425781-pm-raw-uploads/sample.pdf",
        licences=[
            LicenceEntry(
                assetId="src-1",
                assetType="source_text",
                uri="https://openstax.org/books/biology-2e",
                licenceSpdx="CC-BY-4.0",
                attribution="OpenStax Biology 2e"
            )
        ]
    )
    dumped = job.model_dump()
    assert dumped["state"] == "queued"
    assert dumped["costCapUsd"] == 5.0

def test_security_rules_policy_assertions():
    fs_rules = Path("/content/papermorph-studio/firestore.rules").read_text()
    st_rules = Path("/content/papermorph-studio/storage.rules").read_text()
    assert "isOwner(resource.data.ownerUid)" in fs_rules
    assert "allow update, delete: if false;" in fs_rules
    assert "request.auth.uid == uid" in st_rules
    assert "50 * 1024 * 1024" in st_rules

def test_live_firestore_roundtrip_and_ttl():
    db = firestore.Client(project=PROJECT_ID)
    job_ref = db.collection("jobs").document("phase2-verify-job")
    job = JobDoc(
        jobId="phase2-verify-job",
        ownerUid="verify-uid",
        title="Phase 2 Firestore Verification",
        format=ContentFormat.PICTURE_BOOK,
        language=LanguageCode.FA,
        sourceUri="gs://gen-lang-client-0484425781-pm-raw-uploads/fairy.txt"
    )
    job_ref.set(job.model_dump())
    snap = job_ref.get()
    assert snap.exists
    assert snap.to_dict()["language"] == "fa"

    evt_ref = job_ref.collection("events").document("evt-001")
    evt = EventDoc(
        eventId="evt-001",
        jobId="phase2-verify-job",
        stage="ingesting",
        agent="ingestor",
        message="Verified Firestore TTL event",
        expireAt=(datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
    )
    evt_ref.set(evt.model_dump())
    assert evt_ref.get().exists

    # Clean up test docs
    evt_ref.delete()
    job_ref.delete()
