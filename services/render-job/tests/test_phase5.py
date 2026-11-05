import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path("/content/papermorph-studio")
sys.path.insert(0, str(REPO_ROOT / "services" / "render-job" / "vendor"))
sys.path.insert(0, str(REPO_ROOT / "services" / "render-job"))

from papermorph import PapermorphEngine, RenderSpec, SceneSpec
from papermorph.engine import shape_text
from src.render_shard import (
    execute_cloud_run_shard,
    concat_shards_lossless,
    render_vertical_short,
    build_contact_sheet,
)

def build_sample_spec(lang: str = "en", total_ms: int = 4000) -> RenderSpec:
    return RenderSpec(
        job_id=f"test-job-{lang}",
        title="فتوسنتز در گیاهان" if lang == "fa" else "Photosynthesis in Plants",
        language=lang,
        total_duration_ms=total_ms,
        scenes=[
            SceneSpec(
                scene_id="scene-01",
                title="واکنش‌های نوری" if lang == "fa" else "Light Reactions",
                narration_text="کلروفیل انرژی نور خورشید را جذب می‌کند." if lang == "fa" else "Chlorophyll absorbs solar photon energy.",
                start_ms=0,
                end_ms=total_ms // 2,
                word_timings=[
                    {"word": "Chlorophyll", "startMs": 0, "endMs": 800},
                    {"word": "absorbs", "startMs": 800, "endMs": 1600},
                ],
                language=lang,
            ),
            SceneSpec(
                scene_id="scene-02",
                title="چرخه کالوین" if lang == "fa" else "Calvin Cycle",
                narration_text="تولید گلوکز در استروما انجام می‌شود." if lang == "fa" else "Glucose synthesis occurs inside the stroma.",
                start_ms=total_ms // 2,
                end_ms=total_ms,
                word_timings=[
                    {"word": "Glucose", "startMs": total_ms // 2, "endMs": (total_ms // 2) + 900},
                ],
                language=lang,
            ),
        ],
    )

def test_persian_rtl_text_shaping():
    raw = "فتوسنتز در گیاهان"
    shaped = shape_text(raw, "fa")
    assert isinstance(shaped, str) and len(shaped) > 0

def test_multi_shard_render_and_lossless_concat():
    spec = build_sample_spec("en", total_ms=4000)
    with tempfile.TemporaryDirectory() as tmpdir:
        s0 = execute_cloud_run_shard(spec, tmpdir, task_index=0, task_count=2)
        s1 = execute_cloud_run_shard(spec, tmpdir, task_index=1, task_count=2)
        assert os.path.exists(s0["outputPath"])
        assert os.path.exists(s1["outputPath"])

        final_mp4 = os.path.join(tmpdir, "final_1080p.mp4")
        merged = concat_shards_lossless([s0["outputPath"], s1["outputPath"]], final_mp4)
        streams = merged["probe"]["streams"]
        v_stream = next(s for s in streams if s["codec_type"] == "video")
        a_stream = next(s for s in streams if s["codec_type"] == "audio")
        assert v_stream["width"] == 1920
        assert v_stream["height"] == 1080
        assert a_stream["codec_name"] == "aac"
        dur = float(merged["probe"]["format"]["duration"])
        assert 3.5 <= dur <= 4.6

def test_vertical_short_and_contact_sheet_farsi():
    spec = build_sample_spec("fa", total_ms=3000)
    with tempfile.TemporaryDirectory() as tmpdir:
        short_mp4 = os.path.join(tmpdir, "short_9x16.mp4")
        short_res = render_vertical_short(spec, short_mp4, duration_ms=2000)
        v_stream = next(s for s in short_res["probe"]["streams"] if s["codec_type"] == "video")
        assert v_stream["width"] == 1080
        assert v_stream["height"] == 1920

        sheet_png = os.path.join(tmpdir, "contact_sheet.png")
        sheet_res = build_contact_sheet(spec, sheet_png)
        assert sheet_res["width"] == 1920
        assert sheet_res["height"] == 720
        assert sheet_res["sizeBytes"] > 5000


def test_vendored_papermorph_mit_and_mathjax_apache_licences():
    vendor_root = Path("/content/papermorph-studio/services/render-job/vendor/papermorph")
    lic_main = (vendor_root / "LICENSE").read_text()
    lic_mj = (vendor_root / "LICENSE-MATHJAX").read_text()
    assert "MIT License" in lic_main
    assert "Apache License" in lic_mj
    assert "MathJax" in lic_mj

def test_engine_direct_2sec_shard(tmp_path):
    spec = RenderSpec(
        job_id="job-direct-2sec",
        title="Direct 2s Shard Test",
        language="en",
        total_duration_ms=2000,
        scenes=[
            SceneSpec(
                scene_id="scene-1",
                title="Test Scene",
                narration_text="Rendering a two second shard directly with PapermorphEngine.",
                start_ms=0,
                end_ms=2000,
            )
        ],
    )
    engine = PapermorphEngine(spec)
    out_mp4 = str(tmp_path / "shard_2s.mp4")
    res = engine.render_shard_mp4(0, 2000, out_mp4)
    assert res["durationMs"] == 2000
    assert res["sizeBytes"] > 0
    assert Path(out_mp4).exists()
