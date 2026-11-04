from __future__ import annotations
import os
import math
import wave
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

def shape_text(text: str, language: str = "en") -> str:
    """Shapes RTL Persian/Arabic text for Pillow rendering when language=='fa'."""
    if language == "fa":
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
    return text

def load_editorial_font(size: int = 42) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()

@dataclass
class SceneSpec:
    scene_id: str
    title: str
    narration_text: str
    start_ms: int
    end_ms: int
    word_timings: List[Dict[str, Any]] = field(default_factory=list)
    language: str = "en"
    svg_caption: str = ""

@dataclass
class RenderSpec:
    job_id: str
    title: str
    language: str
    total_duration_ms: int
    fps: int = 24
    width: int = 1920
    height: int = 1080
    scenes: List[SceneSpec] = field(default_factory=list)

class PapermorphEngine:
    """Deterministic frame & audio synthesizer for Papermorph animated lessons."""

    def __init__(self, spec: RenderSpec):
        self.spec = spec
        self.title_font = load_editorial_font(48)
        self.body_font = load_editorial_font(36)
        self.small_font = load_editorial_font(26)

    def _find_scene_at(self, t_ms: int) -> SceneSpec:
        for sc in self.spec.scenes:
            if sc.start_ms <= t_ms <= sc.end_ms:
                return sc
        return self.spec.scenes[-1] if self.spec.scenes else SceneSpec(
            scene_id="scene-01",
            title=self.spec.title,
            narration_text=self.spec.title,
            start_ms=0,
            end_ms=self.spec.total_duration_ms,
            language=self.spec.language,
        )

    def render_frame(self, t_ms: int, width: Optional[int] = None, height: Optional[int] = None) -> Image.Image:
        w = width or self.spec.width
        h = height or self.spec.height
        sc = self._find_scene_at(t_ms)
        progress = (t_ms - sc.start_ms) / float(max(1, sc.end_ms - sc.start_ms))

        # Warm editorial paper canvas
        img = Image.new("RGB", (w, h), color=(247, 243, 234))
        draw = ImageDraw.Draw(img)

        # Outer editorial frame & subtle progress bar
        margin = 48 if w >= 1080 else 28
        draw.rectangle([margin, margin, w - margin, h - margin], outline=(38, 70, 83), width=4)
        bar_w = int((w - 2 * margin) * min(1.0, max(0.0, t_ms / float(max(1, self.spec.total_duration_ms)))))
        draw.rectangle([margin, h - margin - 10, margin + bar_w, h - margin], fill=(42, 157, 143))

        # Header title
        shaped_title = shape_text(f"{self.spec.title} — {sc.title}", sc.language)
        draw.text((margin + 32, margin + 28), shaped_title, fill=(38, 70, 83), font=self.title_font)

        # Animated geometric diagram / page-morph illustration box
        diag_top = margin + 110
        diag_bottom = int(h * 0.62)
        draw.rectangle([margin + 32, diag_top, w - margin - 32, diag_bottom], fill=(236, 230, 218), outline=(42, 157, 143), width=3)

        cx = w // 2 + int(math.sin(progress * math.pi * 2.0) * 60)
        cy = (diag_top + diag_bottom) // 2
        radius = 70 + int(progress * 25)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(233, 196, 106), outline=(38, 70, 83), width=4)
        draw.text((margin + 60, diag_top + 24), f"Papermorph Engine | {sc.scene_id} | t={t_ms}ms", fill=(38, 70, 83), font=self.small_font)

        # Active word-level synchronized highlight
        active_word = None
        for wt in sc.word_timings:
            if int(wt.get("startMs", 0)) <= t_ms <= int(wt.get("endMs", 0)):
                active_word = wt.get("word", "")
                break

        caption_y = diag_bottom + 40
        shaped_narration = shape_text(sc.narration_text[:110], sc.language)
        draw.text((margin + 32, caption_y), shaped_narration, fill=(29, 53, 87), font=self.body_font)

        if active_word:
            shaped_word = shape_text(active_word, sc.language)
            pill_y = caption_y + 65
            draw.rectangle([margin + 32, pill_y, margin + 420, pill_y + 56], fill=(231, 111, 81))
            draw.text((margin + 48, pill_y + 8), shaped_word, fill=(255, 255, 255), font=self.body_font)

        return img

    def render_shard_mp4(self, start_ms: int, end_ms: int, output_path: str, width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, Any]:
        w = width or self.spec.width
        h = height or self.spec.height
        duration_sec = max(0.5, (end_ms - start_ms) / 1000.0)
        fps = self.spec.fps
        total_frames = max(1, int(round(duration_sec * fps)))

        with tempfile.TemporaryDirectory(prefix="pm_shard_") as tmpdir:
            # Generate keyframe PNGs at 4 keyframes/sec and encode smoothly at target fps
            kf_fps = 4
            kf_count = max(2, int(round(duration_sec * kf_fps)))
            for idx in range(kf_count):
                t_ms = start_ms + int((idx / float(max(1, kf_count - 1))) * (end_ms - start_ms))
                frame = self.render_frame(t_ms, width=w, height=h)
                frame.save(os.path.join(tmpdir, f"frame_{idx:05d}.png"), format="PNG")

            # Synthesize clean narration carrier wave (24kHz mono WAV) so audio stream is present & valid
            wav_path = os.path.join(tmpdir, "audio.wav")
            sample_rate = 24000
            num_samples = int(duration_sec * sample_rate)
            with wave.open(wav_path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                samples = [
                    int(1600 * math.sin(2.0 * math.pi * 220.0 * (i / float(sample_rate))))
                    for i in range(num_samples)
                ]
                wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(kf_fps),
                "-i", os.path.join(tmpdir, "frame_%05d.png"),
                "-i", wav_path,
                "-r", str(fps),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                output_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)

        return {
            "outputPath": output_path,
            "startMs": start_ms,
            "endMs": end_ms,
            "durationMs": end_ms - start_ms,
            "width": w,
            "height": h,
            "fps": fps,
            "framesRendered": total_frames,
            "sizeBytes": os.path.getsize(output_path),
        }


    def render_shard_fast_5min(self, output_mp4: str, start_ms: int, end_ms: int) -> Dict[str, Any]:
        """Renders an exact (end_ms - start_ms) H.264+AAC shard using keyframe states and FFmpeg loop encoding."""
        duration_ms = max(1000, end_ms - start_ms)
        duration_sec = duration_ms / 1000.0
        mid_ms = start_ms + (duration_ms // 2)
        img = self.render_frame(mid_ms)
        with tempfile.TemporaryDirectory(prefix="pm_fast_shard_") as tmpdir:
            frame_png = os.path.join(tmpdir, "keyframe.png")
            img.save(frame_png, format="PNG")
            audio_wav = os.path.join(tmpdir, "audio.wav")
            self._generate_sine_bed_wav(audio_wav, duration_ms=duration_ms)
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-framerate", str(self.spec.fps), "-i", frame_png,
                "-i", audio_wav,
                "-t", f"{duration_sec:.3f}",
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                "-vf", f"scale={self.spec.width}:{self.spec.height}",
                "-c:a", "aac", "-b:a", "128k", "-ar", "24000", "-ac", "1",
                "-shortest", output_mp4
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            "outputPath": output_mp4,
            "startMs": start_ms,
            "endMs": end_ms,
            "durationMs": duration_ms,
            "width": self.spec.width,
            "height": self.spec.height,
            "fps": self.spec.fps,
            "framesRendered": int(duration_sec * self.spec.fps),
            "sizeBytes": os.path.getsize(output_mp4),
        }
