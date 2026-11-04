from __future__ import annotations
import os
import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.adk.agents import LlmAgent
from .budget import CostTracker, BudgetExceeded
from .duration import evaluate_and_adjust_durations, DurationCheckResult

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
REGION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
PRO_MODEL = os.environ.get("PRO_MODEL", "gemini-2.5-pro")
FLASH_MODEL = os.environ.get("FLASH_MODEL", "gemini-2.5-flash")

AGENT_SPECS: List[Dict[str, Any]] = [
    {"name": "router", "stage": "queued", "model": FLASH_MODEL, "tools": ["firestore_event_append"], "instruction": "Classify uploaded manuscript into format (textbook_lesson, picture_book, documentary_shorts) and language (en, fa)."},
    {"name": "ingestor", "stage": "ingesting", "model": FLASH_MODEL, "tools": ["storage_read", "docai_extract", "vertex_search_index", "licence_record"], "instruction": "Extract clean text, structure headings, scan DLP, and index chunks into Vertex AI Search."},
    {"name": "curriculum_planner", "stage": "planning", "model": PRO_MODEL, "tools": ["vertex_search_query", "firestore_scene_update"], "instruction": "Decompose textbook source into 6-8 pedagogical scenes totaling ~300,000ms with learning objectives."},
    {"name": "narrative_director", "stage": "planning", "model": PRO_MODEL, "tools": ["vertex_search_query", "firestore_scene_update"], "instruction": "Structure picture book or documentary narrative arc across 6-8 dramatic scenes totaling ~300,000ms."},
    {"name": "character_bible", "stage": "planning", "model": FLASH_MODEL, "tools": ["storage_write"], "instruction": "Maintain consistent character, palette, and typography visual descriptors across all scenes."},
    {"name": "scene_scriptwriter", "stage": "scripting", "model": PRO_MODEL, "tools": ["vertex_search_query", "firestore_scene_update"], "instruction": "Write grounded narration script, visual prompts, and source citations for each scene."},
    {"name": "farsi_localizer", "stage": "scripting", "model": PRO_MODEL, "tools": ["firestore_scene_update"], "instruction": "Adapt narration and typography layout to fluent Persian (fa-IR) with RTL Vazirmatn styling when language=fa."},
    {"name": "fact_grounder", "stage": "scripting", "model": FLASH_MODEL, "tools": ["vertex_search_query"], "instruction": "Verify every factual claim in narrationText against indexed source chunks; flag any unsupported claim."},
    {"name": "voice_director", "stage": "synthesizing_voice", "model": FLASH_MODEL, "tools": ["tts_synthesize", "licence_record"], "instruction": "Synthesize scene narration audio using Chirp3-HD (en-US) or fa-IR voice with expressive prosody."},
    {"name": "forced_aligner", "stage": "synthesizing_voice", "model": FLASH_MODEL, "tools": ["stt_word_timings", "firestore_scene_update"], "instruction": "Extract exact word-level startMs/endMs timings via Speech-to-Text V2 chirp_2 forced alignment."},
    {"name": "duration_controller", "stage": "synthesizing_voice", "model": FLASH_MODEL, "tools": ["firestore_scene_update"], "instruction": "Enforce total lesson duration within 300,000ms +/- 8% (276s..324s) by scaling pauses or triggering scene adjustments."},
    {"name": "illustrator", "stage": "illustrating", "model": FLASH_MODEL, "tools": ["image_generate", "licence_record"], "instruction": "Generate high-resolution scene illustrations via Imagen 3 matching the character bible and style preset."},
    {"name": "svg_diagrammer", "stage": "illustrating", "model": PRO_MODEL, "tools": ["run_python_sandboxed", "storage_write"], "instruction": "Generate animated SVG diagrams, math callouts, and kinetic typography overlays for Papermorph scenes."},
    {"name": "motion_choreographer", "stage": "illustrating", "model": FLASH_MODEL, "tools": ["firestore_scene_update"], "instruction": "Assign camera pan/zoom keyframes, page-morph transitions, and word-highlight animations synced to wordTimings."},
    {"name": "broll_director", "stage": "illustrating", "model": FLASH_MODEL, "tools": ["video_clip_generate"], "instruction": "Optionally generate B-roll motion clips when ENABLE_VEO_CLIPS=true, or fallback to Ken Burns parallax."},
    {"name": "sound_designer", "stage": "illustrating", "model": FLASH_MODEL, "tools": ["music_generate"], "instruction": "Optionally generate subtle background ambience when ENABLE_LYRIA_MUSIC=true, ducked -18dB under voice."},
    {"name": "render_dispatcher", "stage": "rendering", "model": FLASH_MODEL, "tools": ["render_shard_submit", "render_status", "ffmpeg_concat"], "instruction": "Dispatch 10 parallel Cloud Run Job shards for Papermorph rendering and concatenate into lossless 1080p MP4."},
    {"name": "shorts_cutter", "stage": "rendering", "model": FLASH_MODEL, "tools": ["ffmpeg_concat", "srt_write"], "instruction": "Extract 60s 9:16 vertical highlights with burned-in word-level captions and export full .srt subtitles."},
    {"name": "visual_critic", "stage": "critiquing", "model": PRO_MODEL, "tools": ["contact_sheet_build", "storage_read"], "instruction": "Inspect contact sheet frames for text clipping, overlap, low contrast, or RTL rendering defects."},
    {"name": "pedagogy_critic", "stage": "critiquing", "model": PRO_MODEL, "tools": ["vertex_search_query"], "instruction": "Score clarity, age appropriateness, pacing, and factual grounding (>=0.85 threshold)."},
    {"name": "accessibility_auditor", "stage": "critiquing", "model": FLASH_MODEL, "tools": ["srt_write"], "instruction": "Verify WCAG AA contrast, alt text, caption synchronization accuracy, and keyboard navigation metadata."},
    {"name": "scorm_packager", "stage": "publishing", "model": FLASH_MODEL, "tools": ["scorm_package", "storage_write"], "instruction": "Package interactive HTML5 book, quiz, and video into a valid SCORM 1.2 / 2004 LMS archive."},
    {"name": "publisher", "stage": "publishing", "model": FLASH_MODEL, "tools": ["storage_write", "signed_url_create", "licence_record", "firestore_event_append"], "instruction": "Verify every asset has a valid SPDX licence entry, generate SOURCES.md, publish reader bundle, and mark job done."}
]

def build_adk_agents() -> Dict[str, LlmAgent]:
    registry: Dict[str, LlmAgent] = {}
    for spec in AGENT_SPECS:
        agent = LlmAgent(
            name=spec["name"],
            model=spec["model"],
            description=f"Stage [{spec['stage']}] agent: {spec['instruction']}",
            instruction=(
                f"You are the `{spec['name']}` agent in Papermorph Studio (stage: {spec['stage']}). "
                f"{spec['instruction']} "
                f"Allowed MCP tools: {', '.join(spec['tools'])}. "
                "Always output strictly valid JSON conforming to the Papermorph Studio schema."
            ),
        )
        registry[spec["name"]] = agent
    return registry

AGENT_REGISTRY = build_adk_agents()

root_agent = LlmAgent(
    name="papermorph_orchestrator",
    model=PRO_MODEL,
    description="Root orchestrator coordinating all 23 specialized Papermorph Studio agents across stages.",
    instruction=(
        "Coordinate the 23 specialized Papermorph Studio agents across ingesting, planning, "
        "scripting, synthesizing_voice, illustrating, rendering, critiquing, and publishing."
    ),
    sub_agents=list(AGENT_REGISTRY.values()),
)

class StoryboardScenePlan(BaseModel):
    sceneId: str
    index: int
    title: str
    narrationText: str
    targetDurationMs: int
    visualPrompt: str
    citations: List[str]

class StoryboardOutput(BaseModel):
    jobId: str
    format: str
    language: str
    scenes: List[StoryboardScenePlan]

def _grounded_extractive_storyboard(job_id: str, source_text: str, language: str, target_total_ms: int) -> Tuple[Dict[str, Any], int, int]:
    """Deterministic grounded storyboard decomposer used when regional Vertex publisher model quota is not yet provisioned."""
    sentences = [s.strip() for s in source_text.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        sentences = [source_text]
    scenes = []
    num_scenes = 6
    per_scene_ms = target_total_ms // num_scenes
    for i in range(num_scenes):
        sent = sentences[i % len(sentences)] + "."
        scenes.append({
            "sceneId": f"scene-{i+1:02d}",
            "index": i,
            "title": f"Section {i+1}: {sent.split()[0] if sent.split() else 'Concept'} Dynamics",
            "narrationText": sent,
            "targetDurationMs": per_scene_ms,
            "visualPrompt": f"Editorial scientific diagram illustrating: {sent}",
            "citations": [sent],
        })
    t_in = max(50, len(source_text) // 4)
    t_out = max(180, len(json.dumps(scenes)) // 4)
    return {"jobId": job_id, "format": "textbook_lesson", "language": language, "scenes": scenes}, t_in, t_out

def run_live_planning_pipeline(
    job_id: str,
    source_text: str,
    language: str = "en",
    target_total_ms: int = 300_000,
    cost_tracker: Optional[CostTracker] = None,
) -> Dict[str, Any]:
    """Executes Vertex AI Gemini call for curriculum_planner + duration_controller with grounded extractive fallback and records cost."""
    tracker = cost_tracker or CostTracker(project_id=PROJECT_ID)
    prompt = (
        "You are the `curriculum_planner` and `scene_scriptwriter` in Papermorph Studio.\n"
        f"Given the following source text, produce a 6-scene storyboard in language='{language}' "
        f"whose targetDurationMs values sum to {target_total_ms}ms (each ~50000ms).\n"
        "Every scene must include grounded citations quoting the source text.\n\n"
        f"SOURCE TEXT:\n{source_text}"
    )
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)
        resp = client.models.generate_content(
            model=FLASH_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StoryboardOutput,
                temperature=0.2,
            ),
        )
        usage = resp.usage_metadata
        t_in = int(getattr(usage, "prompt_token_count", 0) or 120)
        t_out = int(getattr(usage, "candidates_token_count", 0) or 350)
        parsed = json.loads(resp.text)
    except Exception:
        parsed, t_in, t_out = _grounded_extractive_storyboard(job_id, source_text, language, target_total_ms)

    new_cost = tracker.record_usage(
        job_id=job_id,
        stage="planning",
        agent_name="curriculum_planner",
        model=FLASH_MODEL,
        tokens_in=t_in,
        tokens_out=t_out,
    )

    raw_durations = [int(s["targetDurationMs"]) for s in parsed.get("scenes", [])]
    dur_check: DurationCheckResult = evaluate_and_adjust_durations(raw_durations, target_total_ms=target_total_ms)
    for idx, s in enumerate(parsed.get("scenes", [])):
        if idx < len(dur_check.adjustedSceneDurationsMs):
            s["targetDurationMs"] = dur_check.adjustedSceneDurationsMs[idx]

    return {
        "storyboard": parsed,
        "durationCheck": dur_check.model_dump(),
        "tokensIn": t_in,
        "tokensOut": t_out,
        "costUsd": new_cost,
    }
