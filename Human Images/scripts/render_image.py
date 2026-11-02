#!/usr/bin/env python3
"""Render images with Nano Banana Pro (Gemini 3 Pro Image) through the Google Gemini API.

Usage:
  python3 "Human Images/scripts/render_image.py" render PROMPT_FILE \
      --aspect-ratio 4:5 --resolution 2k --output-dir "Human Images/output/RUN_ID" \
      [--reference image.png ...] [--count 1]

Needs the GEMINI_API_KEY environment variable. Uses only the Python standard library.
"""

import argparse
import base64
import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "gemini-3-pro-image-preview"  # Nano Banana Pro
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

ASPECT_RATIOS = ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "4:5", "5:4", "9:16", "16:9", "21:9"]
RESOLUTIONS = {"1k": "1K", "2k": "2K", "4k": "4K"}
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def build_request(prompt, aspect_ratio, resolution, references):
    parts = [{"text": prompt}]
    for ref in references:
        path = Path(ref)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        parts.append({"inline_data": {"mime_type": mime, "data": data}})

    image_config = {"imageSize": RESOLUTIONS[resolution]}
    if aspect_ratio != "auto":
        image_config["aspectRatio"] = aspect_ratio

    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": image_config,
        },
    }


def call_api(model, body, api_key, retries=3):
    req = urllib.request.Request(
        API_URL.format(model=model),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    ctx = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")
            # Retry only on rate limits and server errors.
            if err.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = 2 ** (attempt + 1)
                print(f"HTTP {err.code}, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            sys.exit(f"API error {err.code}: {detail}")
        except urllib.error.URLError as err:
            if attempt < retries:
                time.sleep(2 ** (attempt + 1))
                continue
            sys.exit(f"Network error: {err.reason}")


def save_images(response, output_dir, index):
    saved, notes = [], []
    for cand in response.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and not part.get("thought"):
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                name = f"image_{index:02d}{'' if not saved else f'_{len(saved)}'}{EXTENSIONS.get(mime, '.png')}"
                path = output_dir / name
                path.write_bytes(base64.b64decode(inline["data"]))
                saved.append(path)
            elif part.get("text") and not part.get("thought"):
                notes.append(part["text"])
        if not saved and cand.get("finishReason") not in (None, "STOP"):
            notes.append(f"finishReason: {cand.get('finishReason')}")
    if not saved and response.get("promptFeedback"):
        notes.append(f"promptFeedback: {json.dumps(response['promptFeedback'])}")
    return saved, notes


def cmd_render(args):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set. Add it to the environment settings and start a new session.")

    prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    body = build_request(prompt, args.aspect_ratio, args.resolution, args.reference or [])
    meta = {
        "model": args.model,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
        "references": args.reference or [],
        "prompt_chars": len(prompt),
        "images": [],
    }

    for i in range(1, args.count + 1):
        print(f"Rendering {i}/{args.count} with {args.model}...", file=sys.stderr)
        response = call_api(args.model, body, api_key)
        saved, notes = save_images(response, output_dir, i)
        for note in notes:
            print(f"Model note: {note}", file=sys.stderr)
        if not saved:
            sys.exit("No image returned. See the notes above.")
        for path in saved:
            print(path)
            meta["images"].append(str(path))

    (output_dir / "render.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Nano Banana Pro renderer (Gemini API)")
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Render a prompt file")
    render.add_argument("prompt_file")
    render.add_argument("--aspect-ratio", default="4:5", choices=ASPECT_RATIOS)
    render.add_argument("--resolution", default="2k", choices=list(RESOLUTIONS))
    render.add_argument("--output-dir", required=True)
    render.add_argument("--reference", action="append", help="Reference image (repeatable)")
    render.add_argument("--count", type=int, default=1, help="Number of images to render")
    render.add_argument("--model", default=DEFAULT_MODEL)
    render.set_defaults(func=cmd_render)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
