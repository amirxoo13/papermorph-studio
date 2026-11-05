#!/usr/bin/env python3
"""Paint one picture with Vertex AI Gemini image generation and log its cost.

Drop-in replacement for paint_openai.py using Google Cloud Vertex AI credits:

    python3 paint_vertex.py OUT.png "prompt" [ref.png ...] \
        [--ar 16:9] [--q low|medium] [--bg auto|transparent|opaque] \
        [--model MODEL] --ledger books/<book>/art/costs.tsv
    python3 paint_vertex.py --total books/<book>/art/costs.tsv
"""
import argparse
import time
import io
import mimetypes
import os
import pathlib
import sys

import numpy as np
from PIL import Image
from google import genai
from google.genai import types


def _load_ledger():
    candidates = []
    if os.environ.get("PAPERMORPH_SCRIPTS"):
        candidates.append(pathlib.Path(os.environ["PAPERMORPH_SCRIPTS"]))
    candidates.append(pathlib.Path("/app/vendor/papermorph/.claude/skills/papermorph/scripts"))
    candidates.append(
        pathlib.Path(__file__).resolve().parent
        / "vendor/papermorph/.claude/skills/papermorph/scripts"
    )
    for c in candidates:
        if (c / "ledger.py").is_file():
            sys.path.insert(0, str(c))
            import ledger  # type: ignore
            return ledger.append, ledger.print_total
    raise RuntimeError(
        f"FATAL: ledger.py not found in any candidate path: {[str(c) for c in candidates]}"
    )


append, print_total = _load_ledger()

RETRY_WAITS = [35, 65, 95, 125]   # seconds; the measured limit is about 2 requests per minute


def _generate_with_backoff(client, model, contents, aspect_ratio):
    """Call Vertex, waiting out 429 RESOURCE_EXHAUSTED. Bounded: after the last
    wait the exception is re-raised verbatim and the caller exits non-zero.
    Every wait is printed, so a slow run is visible rather than silent."""
    last = None
    for attempt in range(len(RETRY_WAITS) + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
        except Exception as exc:
            text = str(exc)
            quota = "RESOURCE_EXHAUSTED" in text or "429" in text
            if not quota or attempt == len(RETRY_WAITS):
                raise
            wait = RETRY_WAITS[attempt]
            print(f"quota hit (429); waiting {wait}s then retrying "
                  f"({attempt + 1}/{len(RETRY_WAITS)})", file=sys.stderr, flush=True)
            time.sleep(wait)
            last = exc
    raise last

DEFAULT_MODELS = {
    "low": "gemini-3.1-flash-image",
    "medium": "gemini-3-pro-image",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", nargs="?", help="Output PNG path")
    ap.add_argument("prompt", nargs="?", help="Text prompt")
    ap.add_argument("refs", nargs="*", help="Optional reference image paths")
    ap.add_argument("--ar", default="16:9", help="Aspect ratio (default: 16:9)")
    ap.add_argument("--q", default="medium", help="Quality tier: low or medium (high is refused)")
    ap.add_argument(
        "--bg",
        default="auto",
        choices=["auto", "transparent", "opaque"],
        help="Background mode",
    )
    ap.add_argument("--model", default=None, help="Explicit Vertex model id")
    ap.add_argument("--ledger", default=None, help="Path to costs.tsv ledger")
    ap.add_argument("--total", metavar="LEDGER", help="Print ledger total and exit")
    ap.add_argument("--force", action="store_true", help="Overwrite existing output file")
    ap.add_argument(
        "--usd",
        type=float,
        default=None,
        help="Optional USD cost to record; defaults to 0.0 (Cloud Billing is authoritative)",
    )
    args = ap.parse_args()

    if args.total:
        print_total(pathlib.Path(args.total), ", vertex")
        return 0

    if args.q == "high":
        print(
            "ERROR: --q high is refused: high costs several times as much and has never been needed.",
            file=sys.stderr,
        )
        return 2
    if args.q not in ("low", "medium"):
        print(f"ERROR: --q must be low or medium (got {args.q!r})", file=sys.stderr)
        return 2

    if not args.out or not args.prompt:
        ap.error("OUT.png and prompt are required unless --total is used")
    if not args.ledger:
        ap.error("--ledger is required when painting a picture")

    out_path = pathlib.Path(args.out)
    if out_path.exists() and not args.force:
        print(
            f"ERROR: {out_path} already exists; refusing to overwrite without --force.",
            file=sys.stderr,
        )
        return 3

    model = args.model or DEFAULT_MODELS[args.q]
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
    location = os.environ.get("VERTEX_LOCATION", "global")

    contents = []
    for ref in args.refs:
        ref_path = pathlib.Path(ref)
        if not ref_path.is_file():
            print(f"ERROR: reference image not found: {ref_path}", file=sys.stderr)
            return 4
        mime, _ = mimetypes.guess_type(str(ref_path))
        contents.append(
            types.Part.from_bytes(data=ref_path.read_bytes(), mime_type=mime or "image/png")
        )

    prompt_text = args.prompt
    if args.bg == "transparent":
        prompt_text = (
            f"{prompt_text}. Isolated cut-out subject on a plain transparent/clean background, "
            "no scene or backdrop."
        )
    contents.append(prompt_text)

    try:
        client = genai.Client(vertexai=True, project=project, location=location)
        resp = _generate_with_backoff(client, model, contents, args.ar)
    except Exception as exc:
        print(f"FATAL Vertex API error ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    blob = None
    if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                blob = part.inline_data

    if blob is None:
        print(f"FATAL: model {model} returned no inline_data image part.", file=sys.stderr)
        print("RAW usage_metadata:", resp.usage_metadata, file=sys.stderr)
        return 1

    im = Image.open(io.BytesIO(blob.data))
    im.load()
    arr = np.asarray(im.convert("RGB")).astype("float32")
    stddev = float(arr.std())
    if stddev < 1.0:
        print(f"FATAL: image pixel stddev is {stddev:.3f} (< 1.0, blank image)", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="PNG")

    saved = Image.open(out_path)
    has_alpha = saved.mode in ("RGBA", "LA") or ("transparency" in saved.info)

    print(f"out: {out_path}  model: {model}  size: {saved.size}  mode: {saved.mode}  stddev: {stddev:.3f}")
    print("RAW usage_metadata:", resp.usage_metadata)
    if args.bg == "transparent":
        if has_alpha:
            print("bg=transparent check: returned PNG HAS an alpha channel.")
        else:
            print(
                f"bg=transparent check: returned PNG does NOT have an alpha channel (mode={saved.mode}); "
                "Vertex returned an opaque image."
            )

    if args.usd is None:
        cost = 0.0
        print("cost: recorded $0.0000 in ledger (no --usd given; authoritative cost is Cloud Billing)")
    else:
        cost = float(args.usd)

    what = f"{args.q} {args.ar}"
    if args.bg != "auto":
        what += f" {args.bg}"
    append(pathlib.Path(args.ledger), out_path, model, what, cost)
    return 0


if __name__ == "__main__":
    sys.exit(main())
