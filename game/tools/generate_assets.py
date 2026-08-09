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

from PIL import Image

CHROMA_KEY = (255, 0, 255)  # magenta backdrop for sprite cutouts
CHROMA_TOLERANCE = 60

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


def cut_out_chroma_key(path: Path):
    """Turn the magenta backdrop into real alpha transparency, suppress the
    magenta spill left on anti-aliased edge pixels, and crop to content."""
    img = Image.open(path).convert("RGBA")
    data = img.getdata()
    kr, kg, kb = CHROMA_KEY
    new_data = []
    for r, g, b, a in data:
        dist = ((r - kr) ** 2 + (g - kg) ** 2 + (b - kb) ** 2) ** 0.5
        if dist < CHROMA_TOLERANCE:
            new_data.append((r, g, b, 0))
            continue
        # despill: magenta contamination shows as R and B both running
        # ahead of G; pull them back toward G so edge pixels stop reading pink/purple
        excess = min(r, b) - g
        if excess > 0:
            r = max(0, r - excess)
            b = max(0, b - excess)
        new_data.append((r, g, b, a))
    img.putdata(new_data)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(path)
    print(f"cut out chroma key + cropped {path} -> {img.size}")


CHROMA_PROMPT_SUFFIX = (
    " Full body, standing pose, isolated on a completely flat solid magenta "
    "background (#FF00FF), no shadow, no scenery, no floor, no vignette, no "
    "gradient — a single flat magenta fill behind the character only. "
    "No text or logos in the image."
)

JOBS = [
    dict(
        out="fortress-hero.png",
        refs=["f7a0ab15-IMG_8928.jpeg", "8abc7558-IMG_8929.jpeg"],
        cutout=False,
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
        cutout=False,
        prompt=(
            "Redraw this commander as a clean character portrait: same "
            "peaked cap, gas mask with glowing purple lenses, long black "
            "coat with purple piping, same pose and proportions. Plain dark "
            "vignette background, waist-up, front-facing, suitable as a "
            "game HUD portrait. No text or logos in the image."
        ),
    ),
    dict(
        out="arena-background.png",
        refs=["f7a0ab15-IMG_8928.jpeg", "8abc7558-IMG_8929.jpeg"],
        cutout=False,
        prompt=(
            "Using these two fortress images as architectural reference, paint "
            "a top-down bird's-eye view (looking straight down, like a video "
            "game map, NOT a front or side elevation) of the fortress's main "
            "courtyard interior: a wide stone-and-concrete plaza with three "
            "large gated tunnel entrances arranged along the far edge (one "
            "centered and larger, one to each side) that raiders could pour "
            "through, and a raised command console/altar with the purple "
            "winged emblem at the near edge where a commander would stand. "
            "Same gothic-industrial concrete architecture, purple glowing "
            "accents and banners, dusted with snow, dramatic top-down "
            "lighting. 16:9 aspect ratio. No text, no logos, no people or "
            "characters in the shot."
        ),
    ),
    dict(
        out="terrain-ground.png",
        refs=["2a9a5cce-IMG_8931.jpeg"],
        cutout=False,
        prompt=(
            "Using this snowy mountain valley photo as reference for ground "
            "material, generate a photorealistic aerial/top-down texture of "
            "rocky, snow-patched mountain valley ground: churned snow, dirt, "
            "exposed rock and gravel, tire and foot tracks, cold overcast "
            "lighting with no strong directional shadows so it reads evenly "
            "from any angle. Seamless, uniformly-distributed detail edge to "
            "edge with no single focal object, so it can tile as a repeating "
            "ground texture. Square image, no text, no logos, no people or "
            "vehicles in the shot."
        ),
    ),
    dict(
        out="mountain-skyline.png",
        refs=["f7a0ab15-IMG_8928.jpeg", "2a9a5cce-IMG_8931.jpeg"],
        cutout=False,
        prompt=(
            "Using these two images as reference, paint a wide panoramic "
            "photorealistic mountain skyline: jagged snow-capped peaks under "
            "a heavy overcast stormy sky, matching the cold, dramatic "
            "mountain range visible behind the fortress in the first image. "
            "Very wide aspect ratio horizon backdrop, no foreground "
            "buildings, no people, no vehicles, no text or logos — just the "
            "mountains and sky, suitable as a horizon backdrop panel."
        ),
    ),
    dict(
        out="sprite-player.png",
        refs=["e8423460-IMG_8933.jpeg"],
        cutout=True,
        prompt=(
            "Redraw this commander as a photorealistic full-body render in "
            "the same cinematic, realistic rendering style as the reference "
            "photo itself — not a cartoon, not cel-shaded, not a comic/ink "
            "style, but photoreal detail, materials, and lighting like a "
            "high-end game cinematic. Eye-level, straight-on front view, "
            "standing pose, same peaked cap, gas mask with glowing purple "
            "lenses, long black coat with purple piping, holding a rifle "
            "aimed toward the camera."
            + CHROMA_PROMPT_SUFFIX
        ),
    ),
    dict(
        out="sprite-ally.png",
        refs=["d5972bba-IMG_8932.jpeg"],
        cutout=True,
        prompt=(
            "Redraw the right-hand soldier (the one in the plain black "
            "coat with the tank-and-hose gas mask, no purple pattern gear) "
            "as a photorealistic full-body render in the same cinematic, "
            "realistic rendering style as the reference photo itself — not "
            "a cartoon, not cel-shaded, not a comic/ink style. Eye-level, "
            "straight-on front view, standing pose, holding a rifle aimed "
            "toward the camera, same coat and gas mask design."
            + CHROMA_PROMPT_SUFFIX
        ),
    ),
    dict(
        out="sprite-enemy.png",
        refs=["d5972bba-IMG_8932.jpeg"],
        cutout=True,
        prompt=(
            "Using the soldier's silhouette, gear, and gas-mask design in "
            "this photo as a starting point, redesign it as a RIVAL hostile "
            "faction trooper: same style of military coat, webbing and gas "
            "mask, but recolor all purple/blue accents to a burnt "
            "orange/red color scheme instead, as if it belongs to an enemy "
            "raider faction. Photorealistic full-body render in the same "
            "cinematic, realistic rendering style as the reference photo "
            "itself — not a cartoon, not cel-shaded, not a comic/ink style. "
            "Eye-level, straight-on front view, standing pose, holding a "
            "rifle aimed toward the camera."
            + CHROMA_PROMPT_SUFFIX
        ),
    ),
]


def main():
    only = set(sys.argv[1:])
    api_key = load_api_key()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    for job in JOBS:
        if only and job["out"] not in only:
            continue
        refs = [UPLOADS / name for name in job["refs"]]
        out_path = ASSETS_DIR / job["out"]
        success = generate(api_key, job["prompt"], refs, out_path)
        if success and job.get("cutout"):
            cut_out_chroma_key(out_path)
        ok = success and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
