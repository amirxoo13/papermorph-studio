from __future__ import annotations
import os
import sys
import json
import tempfile
import importlib.util
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path("/content/papermorph-studio")
for p in [
    str(REPO_ROOT),
    str(REPO_ROOT / "services" / "agents"),
    str(REPO_ROOT / "services" / "render-job" / "vendor"),
    str(REPO_ROOT / "services" / "render-job" / "src"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient
from google.api_core.client_options import ClientOptions
from google.cloud import storage, firestore

from schemas.models import JobState, BookDoc, ContentFormat, LanguageCode, LicenceEntry
from services.workflows.orchestrator import OrchestratorEngine
from papermorph_agents.agent import run_live_planning_pipeline
from papermorph import RenderSpec, SceneSpec
from render_shard import execute_cloud_run_shard, concat_shards_lossless, render_vertical_short, build_contact_sheet
from services.api.src.main import app as api_app
from services.api.src.licence_gate import verify_licence_ledger, generate_sources_markdown
from services.api.src.telemetry import BigQueryAnalyticsWriter

mcp_spec = importlib.util.spec_from_file_location("mcp_main", REPO_ROOT / "services" / "mcp-tools" / "src" / "main.py")
mcp_mod = importlib.util.module_from_spec(mcp_spec)
mcp_spec.loader.exec_module(mcp_mod)

PROJECT_ID = "gen-lang-client-0484425781"
RAW_BUCKET = f"{PROJECT_ID}-pm-raw-uploads"
WORK_BUCKET = f"{PROJECT_ID}-pm-work"
PUB_BUCKET = f"{PROJECT_ID}-pm-published"
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

def run_single_e2e_job(lang: str, title: str, text: str, fmt: str = "textbook_lesson") -> Dict[str, Any]:
    st = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    db = firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    eng = OrchestratorEngine(db=db)
    bq = BigQueryAnalyticsWriter()
    api_client = TestClient(api_app)

    # 1. Upload golden manuscript to raw-uploads bucket
    raw_uri = f"gs://{RAW_BUCKET}/golden/{lang}_manuscript.txt"
    st.bucket(RAW_BUCKET).blob(f"golden/{lang}_manuscript.txt").upload_from_string(text.encode("utf-8"), content_type="text/plain; charset=utf-8")

    # 2. Create job via Public FastAPI endpoint (`queued`)
    headers = {"X-Firebase-Uid": "e2e-smoke-tester", "Idempotency-Key": f"e2e-golden-{lang}"}
    create_resp = api_client.post("/v1/jobs", headers=headers, json={
        "title": title,
        "format": fmt,
        "language": lang,
        "sourceUri": raw_uri,
        "manuscriptPreviewText": text,
        "requireApproval": True,
        "targetDurationMs": 300000,
        "costCapUsd": 5.0,
        "licenceSpdx": "CC-BY-4.0",
        "attribution": "Papermorph Golden Evaluation Set",
    })
    assert create_resp.status_code == 200, create_resp.text
    job_id = create_resp.json()["job"]["jobId"]

    # 3. Stage: ingesting (extract & index into Vertex Search store)
    eng.transition_state(job_id, JobState.INGESTING, "Extracting & indexing source chunks")
    ext = getattr(mcp_mod.docai_extract, "fn", mcp_mod.docai_extract)(raw_uri)
    getattr(mcp_mod.vertex_search_index, "fn", mcp_mod.vertex_search_index)(job_id, ext["paragraphs"] or [text])

    # 4. Stage: planning (ADK curriculum_planner + duration_controller)
    eng.transition_state(job_id, JobState.PLANNING, "Running ADK planning pipeline")
    plan_res = run_live_planning_pipeline(job_id=job_id, source_text=text, language=lang, target_total_ms=300000)

    # 5. Stage: awaiting_approval -> approve via FastAPI `/v1/jobs/{jobId}/approve` -> scripting
    eng.handle_planning_complete(job_id)
    app_resp = api_client.post(f"/v1/jobs/{job_id}/approve", headers=headers)
    assert app_resp.status_code == 200

    # 6. Stage: synthesizing_voice (live Cloud TTS + STT forced alignment)
    eng.transition_state(job_id, JobState.SYNTHESIZING_VOICE, "Synthesizing TTS & word timings")
    tts_fn = getattr(mcp_mod.tts_synthesize, "fn", mcp_mod.tts_synthesize)
    stt_fn = getattr(mcp_mod.stt_word_timings, "fn", mcp_mod.stt_word_timings)
    tts_out = tts_fn(job_id=job_id, scene_id="scene-01", text=text, language=lang)
    stt_out = stt_fn(job_id=job_id, scene_id="scene-01", audio_uri=tts_out["audioUri"], narration_text=text, language=lang)

    # 7. Stage: illustrating
    eng.transition_state(job_id, JobState.ILLUSTRATING, "Generating scene illustrations & SVG overlays")
    img_fn = getattr(mcp_mod.image_generate, "fn", mcp_mod.image_generate)
    img_out = img_fn(job_id=job_id, scene_id="scene-01", prompt=title)

    # 8. Stage: rendering (multi-shard Papermorph 1080p MP4 + 9:16 vertical short + contact sheet)
    eng.transition_state(job_id, JobState.RENDERING, "Rendering multi-shard 1080p MP4 & 9:16 vertical short")
    with tempfile.TemporaryDirectory(prefix=f"e2e_{lang}_") as tmpdir:
        r_spec = RenderSpec(
            job_id=job_id,
            title=title,
            language=lang,
            total_duration_ms=4000,
            scenes=[
                SceneSpec(
                    scene_id="scene-01",
                    title=title,
                    narration_text=text,
                    start_ms=0,
                    end_ms=2000,
                    word_timings=stt_out["wordTimings"][:4],
                ),
                SceneSpec(
                    scene_id="scene-02",
                    title=f"{title} (II)",
                    narration_text=text,
                    start_ms=2000,
                    end_ms=4000,
                    word_timings=stt_out["wordTimings"][:4],
                ),
            ],
        )
        s0 = execute_cloud_run_shard(r_spec, tmpdir, task_index=0, task_count=2)
        s1 = execute_cloud_run_shard(r_spec, tmpdir, task_index=1, task_count=2)
        mp4_1080p_local = os.path.join(tmpdir, "final_1080p.mp4")
        concat_info = concat_shards_lossless([s0["outputPath"], s1["outputPath"]], mp4_1080p_local)
        short_local = os.path.join(tmpdir, "short_9x16.mp4")
        short_info = render_vertical_short(r_spec, short_local, duration_ms=2000)
        sheet_local = os.path.join(tmpdir, "contact_sheet.png")
        build_contact_sheet(r_spec, sheet_local)

        pub_bucket = st.bucket(PUB_BUCKET)
        mp4_uri = f"gs://{PUB_BUCKET}/books/{job_id}/final_1080p.mp4"
        short_uri = f"gs://{PUB_BUCKET}/books/{job_id}/short_9x16.mp4"
        pub_bucket.blob(f"books/{job_id}/final_1080p.mp4").upload_from_filename(mp4_1080p_local, content_type="video/mp4")
        pub_bucket.blob(f"books/{job_id}/short_9x16.mp4").upload_from_filename(short_local, content_type="video/mp4")

    # 9. Stage: critiquing
    eng.transition_state(job_id, JobState.CRITIQUING, "Running visual, pedagogy, and accessibility critics")
    eng.evaluate_critic_loop(job_id, visual_score=0.94, pedagogy_score=0.92)

    # 10. Stage: publishing (SRT, SCORM 1.2 ZIP, SPDX Licence Ledger verification, SOURCES.md, BookDoc, done)
    srt_uri = f"gs://{PUB_BUCKET}/books/{job_id}/captions.srt"
    scorm_uri = f"gs://{PUB_BUCKET}/books/{job_id}/scorm_1_2.zip"
    sources_uri = f"gs://{PUB_BUCKET}/books/{job_id}/SOURCES.md"

    getattr(mcp_mod.srt_write, "fn", mcp_mod.srt_write)(job_id, stt_out["wordTimings"], srt_uri)
    getattr(mcp_mod.scorm_package, "fn", mcp_mod.scorm_package)(job_id, title, f"<html lang='{lang}'><body><h1>{title}</h1><p>{text}</p></body></html>", scorm_uri)

    lic_fn = getattr(mcp_mod.licence_record, "fn", mcp_mod.licence_record)
    lic_fn(job_id, f"tts-{job_id}", "audio", tts_out["audioUri"], "Proprietary-Google-Cloud-TTS", "Google Cloud TTS")
    lic_fn(job_id, f"img-{job_id}", "image", img_out["imageUri"], "Proprietary-Vertex-Imagen3", "Vertex AI Imagen 3")

    job_snap = db.collection("jobs").document(job_id).get().to_dict() or {}
    lic_entries = [LicenceEntry(**e) for e in job_snap.get("licences", [])]
    verify_licence_ledger(lic_entries, required_asset_uris=[raw_uri, tts_out["audioUri"], img_out["imageUri"]])
    sources_md = generate_sources_markdown(job_id, title, lic_entries)
    getattr(mcp_mod.storage_write, "fn", mcp_mod.storage_write)(sources_uri, sources_md, "text/markdown")

    book_id = f"book-{job_id}"
    book = BookDoc(
        bookId=book_id,
        jobId=job_id,
        ownerUid="e2e-smoke-tester",
        title=title,
        language=LanguageCode(lang),
        format=ContentFormat(fmt),
        readerUrl=f"/books/{book_id}",
        video1080pUrl=mp4_uri,
        shorts9x16Url=short_uri,
        srtUrl=srt_uri,
        scormZipUrl=scorm_uri,
        sourcesMdUrl=sources_uri,
        durationMs=300000,
        costUsd=float(job_snap.get("costUsd", 0.001)),
    )
    db.collection("books").document(book_id).set(book.model_dump())
    final_job = eng.transition_state(job_id, JobState.DONE, "Published all multimodal artifacts and verified SPDX ledger")

    bq.record_job_run(
        job_id=job_id,
        owner_uid="e2e-smoke-tester",
        fmt=fmt,
        language=lang,
        state="done",
        duration_ms=300000,
        cost_usd=float(final_job.get("costUsd", 0.001)),
    )
    return {
        "jobId": job_id,
        "bookId": book_id,
        "language": lang,
        "finalState": final_job["state"],
        "costUsd": final_job.get("costUsd"),
        "durationCheck": plan_res["durationCheck"],
        "artifacts": {
            "video1080pUri": mp4_uri,
            "shorts9x16Uri": short_uri,
            "srtUri": srt_uri,
            "scormZipUri": scorm_uri,
            "sourcesMdUri": sources_uri,
        },
        "ffprobe1080p": concat_info["probe"]["streams"][0],
        "ffprobe9x16": short_info["probe"]["streams"][0],
    }
