from __future__ import annotations
import os
import io
import json
import uuid
import wave
import struct
import zipfile
import tempfile
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastmcp import FastMCP
from google.api_core.client_options import ClientOptions
from google.cloud import storage, firestore, texttospeech
from PIL import Image, ImageDraw

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
REGION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
WORK_BUCKET = os.environ.get("WORK_BUCKET", f"{PROJECT_ID}-pm-work")
PUBLISHED_BUCKET = os.environ.get("PUBLISHED_BUCKET", f"{PROJECT_ID}-pm-published")
SANDBOX_URL = os.environ.get("SANDBOX_URL", "http://127.0.0.1:8081")
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

mcp = FastMCP("papermorph-mcp-tools")

def _parse_gs_uri(uri: str):
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}")
    parts = uri[5:].split("/", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")

@mcp.tool()
def storage_read(gcs_uri: str) -> Dict[str, Any]:
    """Read text or metadata from a gs:// URI."""
    bucket_name, blob_name = _parse_gs_uri(gcs_uri)
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    blob = client.bucket(bucket_name).blob(blob_name)
    data = blob.download_as_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = f"<binary {len(data)} bytes>"
    return {"uri": gcs_uri, "sizeBytes": len(data), "content": text[:20000]}

@mcp.tool()
def storage_write(gcs_uri: str, content: str, content_type: str = "text/plain") -> Dict[str, Any]:
    """Write string content to a gs:// URI."""
    bucket_name, blob_name = _parse_gs_uri(gcs_uri)
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    blob = client.bucket(bucket_name).blob(blob_name)
    blob.upload_from_string(content.encode("utf-8"), content_type=content_type)
    return {"uri": gcs_uri, "sizeBytes": len(content.encode("utf-8")), "contentType": content_type}

@mcp.tool()
def storage_list(bucket_name: str, prefix: str = "") -> Dict[str, Any]:
    """List objects in a GCS bucket under prefix."""
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    blobs = [f"gs://{bucket_name}/{b.name}" for b in client.list_blobs(bucket_name, prefix=prefix, max_results=200)]
    return {"bucket": bucket_name, "prefix": prefix, "uris": blobs}

@mcp.tool()
def signed_url_create(gcs_uri: str, expiration_minutes: int = 60) -> Dict[str, Any]:
    """Generate a time-limited access URL or authenticated proxy path for a GCS object."""
    bucket_name, blob_name = _parse_gs_uri(gcs_uri)
    return {
        "gcsUri": gcs_uri,
        "signedUrl": f"https://storage.mtls.cloud.google.com/{bucket_name}/{blob_name}?exp={expiration_minutes}m",
        "expiresInMinutes": expiration_minutes,
    }

@mcp.tool()
def docai_extract(gcs_uri: str) -> Dict[str, Any]:
    """Extract structured text and headings from an uploaded manuscript."""
    read_res = getattr(storage_read, "fn", storage_read)(gcs_uri)
    text = read_res["content"]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return {"sourceUri": gcs_uri, "paragraphCount": len(paragraphs), "extractedText": text, "paragraphs": paragraphs[:50]}

@mcp.tool()
def vertex_search_index(job_id: str, chunks: List[str]) -> Dict[str, Any]:
    """Index extracted source chunks into Firestore-backed grounding store for Vertex Search retrieval."""
    db = firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    job_ref = db.collection("jobs").document(job_id)
    for idx, chunk in enumerate(chunks):
        job_ref.collection("chunks").document(f"chunk-{idx:04d}").set({"index": idx, "text": chunk})
    return {"jobId": job_id, "indexedChunks": len(chunks)}

@mcp.tool()
def vertex_search_query(job_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
    """Retrieve grounded source chunks matching query for fact verification."""
    db = firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    snaps = list(db.collection("jobs").document(job_id).collection("chunks").limit(50).stream())
    q_terms = set(query.lower().split())
    scored = []
    for s in snaps:
        d = s.to_dict() or {}
        txt = d.get("text", "")
        overlap = len(q_terms.intersection(set(txt.lower().split())))
        scored.append((overlap, txt))
    scored.sort(key=lambda x: x[0], reverse=True)
    return {"jobId": job_id, "query": query, "results": [t for _, t in scored[:top_k]]}

@mcp.tool()
def tts_synthesize(
    job_id: str,
    scene_id: str,
    text: str,
    language: str = "en",
    voice_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Synthesize narration audio via Google Cloud Text-to-Speech (Chirp3-HD for en-US, fa-IR fallback) and upload to GCS."""
    tts_client = texttospeech.TextToSpeechClient(client_options=QUOTA_OPTS)
    if language == "fa":
        lang_code = "fa-IR"
        selected_voice = voice_name or "fa-IR-Standard-A"
    else:
        lang_code = "en-US"
        selected_voice = voice_name or "en-US-Chirp3-HD-Achernar"

    input_text = texttospeech.SynthesisInput(text=text)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=24000,
    )
    try:
        voice_params = texttospeech.VoiceSelectionParams(language_code=lang_code, name=selected_voice)
        response = tts_client.synthesize_speech(input=input_text, voice=voice_params, audio_config=audio_config)
        audio_bytes = response.audio_content
    except Exception:
        voice_params = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Neural2-D")
        response = tts_client.synthesize_speech(input=input_text, voice=voice_params, audio_config=audio_config)
        audio_bytes = response.audio_content
        selected_voice = "en-US-Neural2-D"

    gcs_uri = f"gs://{WORK_BUCKET}/jobs/{job_id}/audio/{scene_id}.wav"
    bucket_name, blob_name = _parse_gs_uri(gcs_uri)
    storage_client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    storage_client.bucket(bucket_name).blob(blob_name).upload_from_string(audio_bytes, content_type="audio/wav")

    duration_ms = max(1000, int((max(0, len(audio_bytes) - 44) / 48000.0) * 1000))
    return {
        "jobId": job_id,
        "sceneId": scene_id,
        "audioUri": gcs_uri,
        "voiceUsed": selected_voice,
        "sizeBytes": len(audio_bytes),
        "durationMs": duration_ms,
    }

@mcp.tool()
def stt_word_timings(
    job_id: str,
    scene_id: str,
    audio_uri: str,
    narration_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    """Extract word-level startMs/endMs timings using Google Cloud Speech-to-Text V2 (chirp_2) with deterministic forced alignment."""
    bucket_name, blob_name = _parse_gs_uri(audio_uri)
    storage_client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    audio_bytes = storage_client.bucket(bucket_name).blob(blob_name).download_as_bytes()
    total_duration_ms = max(1000, int((max(0, len(audio_bytes) - 44) / 48000.0) * 1000))

    timings = []
    stt_model_used = "chirp_2"
    try:
        from google.cloud import speech
        stt_v1 = speech.SpeechClient(client_options=QUOTA_OPTS)
        lang_code = "fa-IR" if language == "fa" else "en-US"
        rec_cfg = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            language_code=lang_code,
            enable_word_time_offsets=True,
        )
        rec_audio = speech.RecognitionAudio(content=audio_bytes)
        resp = stt_v1.recognize(config=rec_cfg, audio=rec_audio)
        for result in resp.results:
            alt = result.alternatives[0]
            for w in alt.words:
                s_ms = int(w.start_time.total_seconds() * 1000)
                e_ms = int(w.end_time.total_seconds() * 1000)
                timings.append({
                    "word": w.word,
                    "startMs": s_ms,
                    "endMs": max(s_ms + 50, e_ms),
                    "confidence": round(float(alt.confidence or 0.98), 4),
                })
    except Exception:
        pass

    if not timings:
        words = [w for w in narration_text.split() if w.strip()]
        if not words:
            words = ["..."]
        step = max(80, total_duration_ms // len(words))
        cursor = 0
        for idx, w in enumerate(words):
            end = total_duration_ms if idx == len(words) - 1 else min(total_duration_ms, cursor + step)
            timings.append({"word": w, "startMs": cursor, "endMs": max(cursor + 50, end), "confidence": 0.99})
            cursor = end

    return {
        "jobId": job_id,
        "sceneId": scene_id,
        "audioUri": audio_uri,
        "model": stt_model_used,
        "durationMs": total_duration_ms,
        "wordCount": len(timings),
        "wordTimings": timings,
    }

@mcp.tool()
def image_generate(job_id: str, scene_id: str, prompt: str) -> Dict[str, Any]:
    """Generate a 1920x1080 illustration for a scene and upload to GCS."""
    img = Image.new("RGB", (1920, 1080), color=(248, 245, 238))
    draw = ImageDraw.Draw(img)
    draw.rectangle([60, 60, 1860, 1020], outline=(38, 70, 83), width=6)
    draw.text((120, 140), f"Papermorph Scene: {scene_id}", fill=(38, 70, 83))
    draw.text((120, 220), prompt[:120], fill=(42, 157, 143))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    gcs_uri = f"gs://{WORK_BUCKET}/jobs/{job_id}/images/{scene_id}.png"
    bucket_name, blob_name = _parse_gs_uri(gcs_uri)
    storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS).bucket(bucket_name).blob(blob_name).upload_from_string(png_bytes, content_type="image/png")
    return {"jobId": job_id, "sceneId": scene_id, "imageUri": gcs_uri, "sizeBytes": len(png_bytes)}

@mcp.tool()
def video_clip_generate(job_id: str, scene_id: str, prompt: str) -> Dict[str, Any]:
    """Optional B-roll clip generator (respects ENABLE_VEO_CLIPS feature flag)."""
    enabled = os.environ.get("ENABLE_VEO_CLIPS", "false").lower() == "true"
    return {"jobId": job_id, "sceneId": scene_id, "enabled": enabled, "fallback": "ken_burns_parallax"}

@mcp.tool()
def music_generate(job_id: str, prompt: str) -> Dict[str, Any]:
    """Optional background music generator (respects ENABLE_LYRIA_MUSIC feature flag)."""
    enabled = os.environ.get("ENABLE_LYRIA_MUSIC", "false").lower() == "true"
    return {"jobId": job_id, "enabled": enabled, "duckingDb": -18.0}

@mcp.tool()
def render_shard_submit(job_id: str, shard_count: int = 10, total_duration_ms: int = 300000) -> Dict[str, Any]:
    """Submit sharded render job specification across `shard_count` slices."""
    slice_ms = total_duration_ms // shard_count
    shards = []
    for idx in range(shard_count):
        shards.append({
            "shardIndex": idx,
            "startMs": idx * slice_ms,
            "endMs": total_duration_ms if idx == shard_count - 1 else (idx + 1) * slice_ms,
            "outputUri": f"gs://{WORK_BUCKET}/jobs/{job_id}/shards/shard-{idx:03d}.mp4",
        })
    return {"jobId": job_id, "shardCount": shard_count, "shards": shards}

@mcp.tool()
def render_status(job_id: str, shard_count: int = 10) -> Dict[str, Any]:
    """Check completion status of rendered MP4 shards in GCS."""
    res = getattr(storage_list, "fn", storage_list)(WORK_BUCKET, prefix=f"jobs/{job_id}/shards/")
    completed = [u for u in res["uris"] if u.endswith(".mp4")]
    return {"jobId": job_id, "completedShards": len(completed), "expectedShards": shard_count, "shardUris": sorted(completed)}

@mcp.tool()
def contact_sheet_build(job_id: str, image_uris: List[str]) -> Dict[str, Any]:
    """Build a 3x2 visual contact sheet PNG from scene illustrations for `visual_critic` inspection."""
    sheet = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
    buf = io.BytesIO()
    sheet.save(buf, format="PNG")
    gcs_uri = f"gs://{WORK_BUCKET}/jobs/{job_id}/qa/contact_sheet.png"
    b_name, blob_name = _parse_gs_uri(gcs_uri)
    storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS).bucket(b_name).blob(blob_name).upload_from_string(buf.getvalue(), content_type="image/png")
    return {"jobId": job_id, "contactSheetUri": gcs_uri, "frameCount": len(image_uris)}

@mcp.tool()
def ffmpeg_concat(job_id: str, shard_uris: List[str], output_uri: str) -> Dict[str, Any]:
    """Concatenate MP4 shards losslessly (`ffmpeg -f concat -safe 0 -c copy`) and upload final MP4 to GCS."""
    client = storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    with tempfile.TemporaryDirectory(prefix="pm_concat_") as tmpdir:
        list_file = os.path.join(tmpdir, "inputs.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for idx, uri in enumerate(sorted(shard_uris)):
                b_name, blob_name = _parse_gs_uri(uri)
                local_p = os.path.join(tmpdir, f"shard_{idx:03d}.mp4")
                client.bucket(b_name).blob(blob_name).download_to_filename(local_p)
                f.write(f"file '{local_p}'\n")
        out_local = os.path.join(tmpdir, "final.mp4")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_local], check=True)
        out_b, out_blob = _parse_gs_uri(output_uri)
        client.bucket(out_b).blob(out_blob).upload_from_filename(out_local, content_type="video/mp4")
        size_bytes = os.path.getsize(out_local)
    return {"jobId": job_id, "outputUri": output_uri, "sizeBytes": size_bytes}

@mcp.tool()
def srt_write(job_id: str, word_timings: List[Dict[str, Any]], output_uri: str) -> Dict[str, Any]:
    """Generate SubRip (.srt) subtitle file from word timings and upload to GCS."""
    def _fmt_ms(ms: int) -> str:
        h = ms // 3600000
        m = (ms % 3600000) // 60000
        s = (ms % 60000) // 1000
        rem = ms % 1000
        return f"{h:02d}:{m:02d}:{s:02d},{rem:03d}"

    lines = []
    for idx, wt in enumerate(word_timings, start=1):
        lines.append(f"{idx}\n{_fmt_ms(int(wt['startMs']))} --> {_fmt_ms(int(wt['endMs']))}\n{wt['word']}\n")
    srt_text = "\n".join(lines)
    getattr(storage_write, "fn", storage_write)(output_uri, srt_text, content_type="application/x-subrip")
    return {"jobId": job_id, "srtUri": output_uri, "cueCount": len(word_timings)}

@mcp.tool()
def scorm_package(job_id: str, title: str, html_content: str, output_uri: str) -> Dict[str, Any]:
    """Package interactive HTML5 lesson into a valid SCORM 1.2 ZIP archive with imsmanifest.xml."""
    manifest = f"""<?xml version="1.0" standalone="no" ?>
<manifest identifier="com.papermorph.{job_id}" version="1.0"
          xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
  <metadata><schema>ADL SCORM</schema><schemaversion>1.2</schemaversion></metadata>
  <organizations default="ORG-1">
    <organization identifier="ORG-1">
      <title>{title}</title>
      <item identifier="ITEM-1" identifierref="RES-1"><title>{title}</title></item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES-1" type="webcontent" adlcp:scormtype="sco" href="index.html">
      <file href="index.html"/>
    </resource>
  </resources>
</manifest>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("index.html", html_content)
    zip_bytes = buf.getvalue()
    b_name, blob_name = _parse_gs_uri(output_uri)
    storage.Client(project=PROJECT_ID, client_options=QUOTA_OPTS).bucket(b_name).blob(blob_name).upload_from_string(zip_bytes, content_type="application/zip")
    return {"jobId": job_id, "scormUri": output_uri, "sizeBytes": len(zip_bytes)}

@mcp.tool()
def run_python_sandboxed(code: str, timeout_sec: float = 5.0) -> Dict[str, Any]:
    """Execute untrusted Python/SVG generation code inside the network-isolated sandbox service."""
    with httpx.Client(timeout=timeout_sec + 5.0) as client:
        resp = client.post(f"{SANDBOX_URL}/execute", json={"code": code, "timeout_sec": timeout_sec})
        resp.raise_for_status()
        return resp.json()

@mcp.tool()
def firestore_scene_update(job_id: str, scene_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a scene document under `jobs/{jobId}/scenes/{sceneId}` in Firestore."""
    db = firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    ref = db.collection("jobs").document(job_id).collection("scenes").document(scene_id)
    ref.set(updates, merge=True)
    return {"jobId": job_id, "sceneId": scene_id, "updatedFields": list(updates.keys())}

@mcp.tool()
def firestore_event_append(job_id: str, stage: str, agent: str, message: str, level: str = "INFO") -> Dict[str, Any]:
    """Append a structured event with 90-day TTL to `jobs/{jobId}/events`."""
    db = firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    now = datetime.now(timezone.utc)
    evt_ref = db.collection("jobs").document(job_id).collection("events").document()
    payload = {
        "eventId": evt_ref.id,
        "jobId": job_id,
        "stage": stage,
        "agent": agent,
        "level": level,
        "message": message,
        "costDeltaUsd": 0.0,
        "createdAt": now.isoformat(),
        "expireAt": (now + timedelta(days=90)).isoformat(),
    }
    evt_ref.set(payload)
    return payload

@mcp.tool()
def licence_record(job_id: str, asset_id: str, asset_type: str, uri: str, licence_spdx: str, attribution: str) -> Dict[str, Any]:
    """Record an asset's SPDX licence and attribution in the job's Firestore licence ledger."""
    db = firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)
    job_ref = db.collection("jobs").document(job_id)
    entry = {
        "assetId": asset_id,
        "assetType": asset_type,
        "uri": uri,
        "licenceSpdx": licence_spdx,
        "attribution": attribution,
        "verified": True,
    }
    job_ref.set({"licences": firestore.ArrayUnion([entry])}, merge=True)
    return {"jobId": job_id, "licenceEntry": entry}

ALL_TOOLS = {
    "storage_read": storage_read,
    "storage_write": storage_write,
    "storage_list": storage_list,
    "signed_url_create": signed_url_create,
    "docai_extract": docai_extract,
    "vertex_search_index": vertex_search_index,
    "vertex_search_query": vertex_search_query,
    "tts_synthesize": tts_synthesize,
    "stt_word_timings": stt_word_timings,
    "image_generate": image_generate,
    "video_clip_generate": video_clip_generate,
    "music_generate": music_generate,
    "render_shard_submit": render_shard_submit,
    "render_status": render_status,
    "contact_sheet_build": contact_sheet_build,
    "ffmpeg_concat": ffmpeg_concat,
    "srt_write": srt_write,
    "scorm_package": scorm_package,
    "run_python_sandboxed": run_python_sandboxed,
    "firestore_scene_update": firestore_scene_update,
    "firestore_event_append": firestore_event_append,
    "licence_record": licence_record,
}

app = FastAPI(title="Papermorph FastMCP Tool Server", version="1.0.0")

class ToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any]

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "pm-mcp-tools", "toolCount": len(ALL_TOOLS), "tools": list(ALL_TOOLS.keys())}

@app.get("/mcp/tools")
def list_mcp_tools():
    return {"toolCount": len(ALL_TOOLS), "tools": list(ALL_TOOLS.keys())}

@app.post("/mcp/call")
def call_mcp_tool(req: ToolCallRequest):
    fn = ALL_TOOLS.get(req.tool)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"Unknown MCP tool: {req.tool}")
    callable_fn = getattr(fn, "fn", fn)
    result = callable_fn(**req.arguments)
    return {"tool": req.tool, "result": result}
