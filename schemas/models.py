from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class JobState(str, Enum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    SCRIPTING = "scripting"
    SYNTHESIZING_VOICE = "synthesizing_voice"
    ILLUSTRATING = "illustrating"
    RENDERING = "rendering"
    CRITIQUING = "critiquing"
    PUBLISHING = "publishing"
    DONE = "done"
    FAILED = "failed"
    PAUSED_BUDGET = "paused_budget"
    CANCELLED = "cancelled"

ALLOWED_TRANSITIONS: Dict[JobState, Set[JobState]] = {
    JobState.QUEUED: {JobState.INGESTING, JobState.FAILED, JobState.CANCELLED},
    JobState.INGESTING: {JobState.PLANNING, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.PLANNING: {JobState.AWAITING_APPROVAL, JobState.SCRIPTING, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.AWAITING_APPROVAL: {JobState.SCRIPTING, JobState.PLANNING, JobState.FAILED, JobState.CANCELLED},
    JobState.SCRIPTING: {JobState.SYNTHESIZING_VOICE, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.SYNTHESIZING_VOICE: {JobState.ILLUSTRATING, JobState.RENDERING, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.ILLUSTRATING: {JobState.RENDERING, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.RENDERING: {JobState.CRITIQUING, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.CRITIQUING: {JobState.PUBLISHING, JobState.SCRIPTING, JobState.ILLUSTRATING, JobState.RENDERING, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.PUBLISHING: {JobState.DONE, JobState.FAILED, JobState.PAUSED_BUDGET, JobState.CANCELLED},
    JobState.PAUSED_BUDGET: {
        JobState.INGESTING, JobState.PLANNING, JobState.SCRIPTING,
        JobState.SYNTHESIZING_VOICE, JobState.ILLUSTRATING, JobState.RENDERING,
        JobState.CRITIQUING, JobState.PUBLISHING, JobState.CANCELLED, JobState.FAILED
    },
    JobState.FAILED: {
        JobState.QUEUED, JobState.INGESTING, JobState.PLANNING, JobState.SCRIPTING,
        JobState.SYNTHESIZING_VOICE, JobState.ILLUSTRATING, JobState.RENDERING,
        JobState.CRITIQUING, JobState.PUBLISHING
    },
    JobState.DONE: set(),
    JobState.CANCELLED: set(),
}

class InvalidStateTransitionError(ValueError):
    pass

def validate_transition(current: JobState, target: JobState) -> bool:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransitionError(f"Illegal state transition: {current.value} -> {target.value}")
    return True

class ContentFormat(str, Enum):
    """One value per engine tier.

    new_book.py takes exactly four tiers: lesson, picture, documentary and
    shorts. DOCUMENTARY_SHORTS collapsed the last two into one value, so a
    caller could not choose between a landscape documentary and an upright
    900x1600 short. It is kept only so existing job documents still parse.
    """

    TEXTBOOK_LESSON = "textbook_lesson"
    PICTURE_BOOK = "picture_book"
    DOCUMENTARY = "documentary"
    SHORT = "short"
    DOCUMENTARY_SHORTS = "documentary_shorts"  # legacy, treated as documentary

class LanguageCode(str, Enum):
    EN = "en"
    FA = "fa"

class WordTiming(BaseModel):
    model_config = ConfigDict(extra="forbid")
    word: str
    startMs: int = Field(ge=0)
    endMs: int = Field(ge=0)
    confidence: float = Field(default=0.99, ge=0.0, le=1.0)

class LicenceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assetId: str
    assetType: str  # "source_text" | "image" | "audio" | "video" | "font" | "engine"
    uri: str
    licenceSpdx: str  # e.g., "CC0-1.0", "CC-BY-4.0", "Proprietary-Vertex-Imagen3"
    attribution: str
    verified: bool = True

class SceneDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sceneId: str
    jobId: str
    index: int = Field(ge=0)
    title: str
    narrationText: str
    targetDurationMs: int = Field(ge=1000)
    actualDurationMs: Optional[int] = None
    visualPrompt: str
    svgOverlaySpec: Optional[str] = None
    audioUri: Optional[str] = None
    imageUri: Optional[str] = None
    videoShardUris: List[str] = Field(default_factory=list)
    wordTimings: List[WordTiming] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    status: str = "pending"

class JobDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jobId: str
    ownerUid: str
    title: str
    format: ContentFormat
    language: LanguageCode = LanguageCode.EN
    stylePresetId: str = "default-editorial"
    sourceUri: str
    state: JobState = JobState.QUEUED
    requireApproval: bool = True
    approvedAt: Optional[str] = None
    targetDurationMs: int = 300000
    actualDurationMs: Optional[int] = None
    costUsd: float = Field(default=0.0, ge=0.0)
    costCapUsd: float = Field(default=5.0, gt=0.0)
    tokensIn: int = Field(default=0, ge=0)
    tokensOut: int = Field(default=0, ge=0)
    stageAttempts: Dict[str, int] = Field(default_factory=dict)
    artifacts: Dict[str, str] = Field(default_factory=dict)
    licences: List[LicenceEntry] = Field(default_factory=list)
    errorMessage: Optional[str] = None
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EventDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eventId: str
    jobId: str
    stage: str
    agent: str
    level: str = "INFO"
    message: str
    costDeltaUsd: float = 0.0
    traceId: Optional[str] = None
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expireAt: str

class BookDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bookId: str
    jobId: str
    ownerUid: str
    title: str
    language: LanguageCode
    format: ContentFormat
    readerUrl: str
    video1080pUrl: str
    shorts9x16Url: Optional[str] = None
    srtUrl: str
    scormZipUrl: Optional[str] = None
    sourcesMdUrl: str
    durationMs: int
    costUsd: float
    publishedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
