#!/usr/bin/env python3
"""Generate Fortress Siege key art from the reference photos via the Gemini
image API. Reads GEMINI_API_KEY from the environment (see ../../.env).

Usage: python3 generate_assets.py
"""
import base64
import json
import mimetypes
import os
import sys
import urllib.request
from pathlib import Path

MODEL = "gemini-3.1-flash-image"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT / "game" / "assets"
UPLOADS = Path("/root/.claude/uploads/bcf67485-5773-56c6-82c7-1142bc5694f0")


def load_api_key():
    env_path = ROOT / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GEMINI_API_KEY not found in .env")


def image_part(path: Path):
    mime, _ = mimetypes.guess_type(str(path))
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inline_data": {"mime_type": mime or "image/jpeg", "data": data}}


def generate(api_key, prompt, ref_images, out_path):
    parts = [{"text": prompt}] + [image_part(p) for p in ref_images]
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    req = urllib.request.Request(
        f"{API_URL}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} generating {out_path.name}:", e.read().decode(), file=sys.stderr)
        return False

    candidates = result.get("candidates", [])
    if not candidates:
        print(f"No candidates for {out_path.name}: {json.dumps(result)[:500]}", file=sys.stderr)
        return False

    for part in candidates[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            out_path.write_bytes(base64.b64decode(inline["data"]))
            print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
            return True

    print(f"No image data returned for {out_path.name}: {json.dumps(result)[:500]}", file=sys.stderr)
    return False


JOBS = [
    dict(
        out="fortress-hero.png",
        refs=["f7a0ab15-IMG_8928.jpeg", "2a9a5cce-IMG_8931.jpeg"],
        prompt=(
            "Combine these two fortress reference images into a single cinematic "
            "hero shot of one fortress: keep the concrete mountain-bunker "
            "architecture, multiple gated tunnel entrances, purple winged "
            "banner emblem, and dark stormy mountain backdrop from the first "
            "image, blended with the gothic keep silhouette and purple glow "
            "accents of the second. 16:9 wide shot, dusk lighting, moody and "
            "imposing, no text or logos in the image."
        ),
    ),
    dict(
        out="commander-portrait.png",
        refs=["e8423460-IMG_8933.jpeg"],
        prompt=(
            "Redraw this commander as a clean character portrait: same "
            "peaked cap, gas mask with glowing purple lenses, long black "
            "coat with purple piping, same pose and proportions. Plain dark "
            "vignette background, waist-up, front-facing, suitable as a "
            "game HUD portrait. No text or logos in the image."
        ),
    ),
]


def main():
    api_key = load_api_key()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    for job in JOBS:
        refs = [UPLOADS / name for name in job["refs"]]
        out_path = ASSETS_DIR / job["out"]
        ok = generate(api_key, job["prompt"], refs, out_path) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
