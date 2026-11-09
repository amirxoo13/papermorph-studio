#!/usr/bin/env python3
import argparse
import os
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright

def get_chrome_path() -> str:
    with sync_playwright() as p:
        return p.chromium.executable_path

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def run_benchmark(chapter: str, url: str, site_dir: str, port: int, out_dir: str, jobs_list: list[int], to_beat: str | None) -> int:
    nproc_out = subprocess.check_output(["nproc"], text=True).strip()
    nproc_val = int(nproc_out)
    print(f"nproc={nproc_val}")

    ff_ver = subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0]
    print(f"ffmpeg_version={ff_ver}")

    chrome = os.environ.get("CHROME") or get_chrome_path()
    os.environ["CHROME"] = chrome
    print(f"CHROME={chrome}")
    if not (os.path.isfile(chrome) and os.access(chrome, os.X_OK)):
        print("ERROR: CHROME is not executable", file=sys.stderr)
        return 1
    print("chromium-ok")

    serve_proc = None
    if not port_open(port):
        serve_proc = subprocess.Popen(
            [sys.executable, "/app/vendor/papermorph/.claude/skills/papermorph/scripts/serve.py" if os.path.isdir("/app/vendor/papermorph") else "vendor/Papermorph/.claude/skills/papermorph/scripts/serve.py", str(port), site_dir],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)

    try:
        check_url = f"{url.rstrip('/')}/{chapter}/"
        with urllib.request.urlopen(check_url, timeout=10) as resp:
            print(f"server:{resp.status}")
            if resp.status != 200:
                return 1

        os.makedirs(out_dir, exist_ok=True)
        for jobs in jobs_list:
            print("=" * 60)
            print(f"RUN jobs={jobs} to_beat={to_beat or 'FULL'}")
            inner_args = [
                "uv", "run", "--with", "playwright", "--with", "numpy",
                "/app/vendor/papermorph/.claude/skills/papermorph/scripts/export.py" if os.path.isdir("/app/vendor/papermorph") else "vendor/Papermorph/.claude/skills/papermorph/scripts/export.py",
                chapter,
                "--url", url,
                "--out", out_dir,
                "--jobs", str(jobs),
            ]
            if to_beat:
                inner_args.extend(["--to", to_beat])

            bash_cmd = "time -p " + " ".join(shlex.quote(a) for a in inner_args)
            print("$ " + bash_cmd)
            p = subprocess.run(["bash", "-c", bash_cmd], text=True, capture_output=True)
            combined = (p.stdout or "") + (p.stderr or "")
            print(combined, end="")
            print(f"[export_exit_status: {p.returncode}]")
            if p.returncode != 0:
                return p.returncode

            mp4_path = os.path.join(out_dir, f"{chapter}.mp4")
            srt_path = os.path.join(out_dir, f"{chapter}.srt")
            if not os.path.isfile(mp4_path) or not os.path.isfile(srt_path):
                print("ERROR: mp4 or srt missing", file=sys.stderr)
                return 1
            srt_lines = len(open(srt_path, encoding="utf-8").read().splitlines())
            print(f"srt_file={srt_path} lines={srt_lines}")

            ffprobe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration,size",
                "-of", "default=nw=1",
                mp4_path,
            ]
            print("$ " + " ".join(ffprobe_cmd))
            fp = subprocess.run(ffprobe_cmd, text=True, capture_output=True, check=True)
            print(fp.stdout, end="")

            dur_m = re.search(r"duration=([0-9.]+)", fp.stdout)
            real_m = re.search(r"^real\s+([0-9.]+)", combined, re.M)
            user_m = re.search(r"^user\s+([0-9.]+)", combined, re.M)
            sys_m = re.search(r"^sys\s+([0-9.]+)", combined, re.M)
            frames_matches = re.findall(r"(\d+)\s+frames", combined)
            frames_m = frames_matches[-1] if frames_matches else None

            if not (dur_m and real_m and user_m and sys_m and frames_m):
                print("ERROR: failed to parse metrics from output", file=sys.stderr)
                return 1

            duration = float(dur_m.group(1))
            real_s = float(real_m.group(1))
            user_s = float(user_m.group(1))
            sys_s = float(sys_m.group(1))
            frames = int(frames_m)

            render_factor = real_s / duration
            parallelism = (user_s + sys_s) / real_s if real_s > 0 else 0.0
            fps = frames / real_s if real_s > 0 else 0.0

            print(
                f"METRICS jobs={jobs}: video_duration={duration:.3f}s real={real_s:.2f}s "
                f"user={user_s:.2f}s sys={sys_s:.2f}s frames={frames} "
                f"render_factor={render_factor:.3f}x parallelism={parallelism:.2f}/{nproc_val}_cores "
                f"fps={fps:.2f}"
            )
        return 0
    finally:
        if serve_proc is not None:
            serve_proc.terminate()
            serve_proc.wait(timeout=5)

def main() -> int:
    ap = argparse.ArgumentParser(description="Papermorph render benchmark harness")
    ap.add_argument("--chapter", default="ch01")
    ap.add_argument("--url", default="http://localhost:8765/madness/")
    ap.add_argument("--site", default="/app/vendor/papermorph/site" if os.path.isdir("/app/vendor/papermorph") else "vendor/Papermorph/site")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--out", default="/tmp/out")
    ap.add_argument("--jobs", default="4,8", help="Comma-separated job counts")
    ap.add_argument("--to", dest="to_beat", default=None, help="Stop after beat ID (for Colab smoke test)")
    args = ap.parse_args()
    jobs_list = [int(x.strip()) for x in args.jobs.split(",") if x.strip()]
    return run_benchmark(args.chapter, args.url, args.site, args.port, args.out, jobs_list, args.to_beat)

if __name__ == "__main__":
    sys.exit(main())
