import sys
from pathlib import Path
from fastapi.testclient import TestClient

REPO_ROOT = Path("/content/papermorph-studio")
sys.path.insert(0, str(REPO_ROOT / "services" / "sandbox"))
from src.main import app as sandbox_app

sys.modules.pop("src.main", None)
sys.modules.pop("src", None)
sys.path.insert(0, str(REPO_ROOT / "services" / "mcp-tools"))
from src.main import app as mcp_app, ALL_TOOLS

sbx_client = TestClient(sandbox_app)
mcp_client = TestClient(mcp_app)

def test_all_22_mcp_tools_exposed():
    r = mcp_client.get("/mcp/tools")
    assert r.status_code == 200
    data = r.json()
    assert data["toolCount"] >= 21
    for required in [
        "storage_read", "storage_write", "storage_list", "signed_url_create",
        "docai_extract", "vertex_search_index", "vertex_search_query",
        "tts_synthesize", "stt_word_timings", "image_generate",
        "video_clip_generate", "music_generate", "render_shard_submit",
        "render_status", "contact_sheet_build", "ffmpeg_concat",
        "srt_write", "scorm_package", "run_python_sandboxed",
        "firestore_scene_update", "firestore_event_append", "licence_record"
    ]:
        assert required in data["tools"]

def test_sandbox_executes_pure_svg_math():
    r = sbx_client.post("/execute", json={"code": "print('<svg width=\"100\" height=\"100\"></svg>')"})
    assert r.status_code == 200
    res = r.json()
    assert res["returncode"] == 0
    assert "<svg" in res["stdout"]

def test_sandbox_blocks_network_egress():
    code = "import urllib.request\nurllib.request.urlopen('https://example.com', timeout=2)\n"
    r = sbx_client.post("/execute", json={"code": code})
    assert r.status_code == 200
    res = r.json()
    assert res["returncode"] != 0
    assert "Network egress is strictly prohibited" in res["stderr"]

def test_live_tts_synthesize_and_stt_word_timings():
    tts_resp = mcp_client.post("/mcp/call", json={
        "tool": "tts_synthesize",
        "arguments": {
            "job_id": "phase4-verify-job",
            "scene_id": "scene-01",
            "text": "Photosynthesis converts sunlight into chemical energy inside plant chloroplasts.",
            "language": "en"
        }
    })
    assert tts_resp.status_code == 200
    tts_res = tts_resp.json()["result"]
    assert tts_res["audioUri"].startswith("gs://")
    assert tts_res["sizeBytes"] > 1000

    stt_resp = mcp_client.post("/mcp/call", json={
        "tool": "stt_word_timings",
        "arguments": {
            "job_id": "phase4-verify-job",
            "scene_id": "scene-01",
            "audio_uri": tts_res["audioUri"],
            "narration_text": "Photosynthesis converts sunlight into chemical energy inside plant chloroplasts.",
            "language": "en"
        }
    })
    assert stt_resp.status_code == 200
    stt_res = stt_resp.json()["result"]
    assert stt_res["wordCount"] >= 5
    assert len(stt_res["wordTimings"]) >= 5
