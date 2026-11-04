from __future__ import annotations
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image

VENDOR_ROOT = Path(__file__).resolve().parent.parent / "vendor"
if str(VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(VENDOR_ROOT))

from papermorph import PapermorphEngine, RenderSpec, SceneSpec

def probe_media(file_path: str) -> Dict[str, Any]:
    """Run ffprobe on a media file and return parsed stream & format metadata."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=index,codec_name,codec_type,width,height,r_frame_rate",
        "-of", "json",
        file_path,
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(res.stdout)

def concat_shards_lossless(shard_paths: List[str], output_path: str) -> Dict[str, Any]:
    """Concatenate MP4 shards losslessly using `ffmpeg -f concat -safe 0 -c copy`."""
    with tempfile.TemporaryDirectory(prefix="pm_concat_local_") as tmpdir:
        list_file = os.path.join(tmpdir, "inputs.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for p in shard_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path],
            check=True,
            capture_output=True,
        )
    return {"outputPath": output_path, "sizeBytes": os.path.getsize(output_path), "probe": probe_media(output_path)}

def render_vertical_short(spec: RenderSpec, output_path: str, duration_ms: int = 4000) -> Dict[str, Any]:
    """Render a 9:16 vertical short (1080x1920) with burned-in word highlights."""
    engine = PapermorphEngine(spec)
    res = engine.render_shard_mp4(0, min(duration_ms, spec.total_duration_ms), output_path, width=1080, height=1920)
    res["probe"] = probe_media(output_path)
    return res

def build_contact_sheet(spec: RenderSpec, output_path: str, cols: int = 3, rows: int = 2) -> Dict[str, Any]:
    """Render a 3x2 contact sheet PNG across the lesson timeline for `visual_critic` QA."""
    engine = PapermorphEngine(spec)
    thumb_w, thumb_h = 640, 360
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), color=(38, 70, 83))
    total_cells = cols * rows
    for idx in range(total_cells):
        t_ms = int(((idx + 0.5) / float(total_cells)) * spec.total_duration_ms)
        frame = engine.render_frame(t_ms, width=1920, height=1080).resize((thumb_w, thumb_h))
        r = idx // cols
        c = idx % cols
        sheet.paste(frame, (c * thumb_w, r * thumb_h))
    sheet.save(output_path, format="PNG")
    return {"outputPath": output_path, "width": cols * thumb_w, "height": rows * thumb_h, "sizeBytes": os.path.getsize(output_path)}

def execute_cloud_run_shard(
    spec: RenderSpec,
    output_dir: str,
    task_index: Optional[int] = None,
    task_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Entrypoint for a single Cloud Run Job task reading CLOUD_RUN_TASK_INDEX / CLOUD_RUN_TASK_COUNT."""
    idx = task_index if task_index is not None else int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
    cnt = task_count if task_count is not None else int(os.environ.get("CLOUD_RUN_TASK_COUNT", "10"))
    slice_ms = spec.total_duration_ms // cnt
    start_ms = idx * slice_ms
    end_ms = spec.total_duration_ms if idx == cnt - 1 else (idx + 1) * slice_ms

    os.makedirs(output_dir, exist_ok=True)
    shard_path = os.path.join(output_dir, f"shard-{idx:03d}.mp4")
    engine = PapermorphEngine(spec)
    res = engine.render_shard_mp4(start_ms, end_ms, shard_path)
    res["taskIndex"] = idx
    res["taskCount"] = cnt
    return res
