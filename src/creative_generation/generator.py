"""Sequence E, Part 3 orchestration. No autonomous visual critic here -
this produces candidates and a manifest; a human picks one. Deterministic
checks only (image_checks.py), never a semantic/visual judgment call.

Expected `creative_brief` shape (loosely typed - whatever's present is
used, nothing is required beyond what's listed as optional below):
{
  "tone": "e.g. bold, minimal, streetwear"                (optional)
  "notes": "additional creative direction"                (optional)
  "competitor_inspiration": "style/mood summary - NOT literal copy"  (optional)
  "caption": "Instagram caption text - used later by Part 4, never
              drawn into the generated image"              (optional)
}
"""
import io
import json
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from . import config
from .gemini_client import generate_image
from .image_checks import ImageCheckError, validate_candidate


def load_reference_bytes(path_or_url: str) -> bytes:
    if path_or_url.startswith(("http://", "https://")):
        request = urllib.request.Request(path_or_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    return Path(path_or_url).read_bytes()


def build_prompt(creative_brief: dict, product: dict, model_reference: str | None = None) -> str:
    tone = creative_brief.get("tone", "")
    notes = creative_brief.get("notes", "")
    competitor_inspiration = creative_brief.get("competitor_inspiration", "")

    lines = [
        f'Create a photorealistic Instagram product photo for the T-shirt "{product.get("title", "")}".',
        "Preserve the exact color, fit, graphic, and any branding shown in the "
        "attached garment reference image(s) exactly as they appear - do not "
        "alter, redesign, or reinterpret the shirt's actual design.",
    ]
    if model_reference:
        lines.append(
            "HIGHEST PRIORITY: a real Samsin model reference image is attached. "
            "Preserve that exact model's identity - face, hair, and clothing - "
            "and this exact Star T-shirt's color, graphic, and fit, unaltered. "
            "Any competitor pose or styling referenced below is inspiration "
            "only, never a requirement: if following it would change the "
            "model's identity or the shirt's actual design, preservation wins "
            "and that competitor cue is skipped."
        )
    if tone:
        lines.append(f"Creative tone/direction: {tone}.")
    if notes:
        lines.append(notes)
    if competitor_inspiration:
        lines.append(
            "Competitor creative context, for style/mood inspiration only - "
            "never copy any competitor logo, layout, or on-image text: "
            f"{competitor_inspiration}"
        )
    lines.append(
        "Do not include any price, discount, promotional claim, watermark, "
        "or any text of any kind rendered into the image."
    )
    lines.append(
        f"Output a single portrait image, exactly {config.CANDIDATE_WIDTH}x"
        f"{config.CANDIDATE_HEIGHT} pixels (4:5 Instagram feed ratio)."
    )
    return "\n".join(lines)


def _cover_resize(image_bytes: bytes, width: int, height: int) -> bytes:
    """Deterministic resize + center-crop to exactly (width, height) - no
    AI, no content regeneration, just standard image scaling. Confirmed
    live: Gemini does not reliably honor an exact pixel size requested via
    prompt text alone (it returned 1024x1024 for a requested 1080x1350),
    so this guarantees the contract regardless of the model's native
    output size."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    image = image.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - width) // 2, (new_h - height) // 2
    image = image.crop((left, top, left + width, top + height))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _generate_one(prompt: str, reference_images: list, api_key: str, model: str, api_base: str) -> dict:
    raw_bytes = generate_image(
        prompt=prompt,
        reference_images=reference_images,
        api_key=api_key,
        model=model,
        api_base=api_base,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    try:
        image_bytes = _cover_resize(raw_bytes, config.CANDIDATE_WIDTH, config.CANDIDATE_HEIGHT)
    except Exception as exc:
        # The resize itself failed (e.g. Gemini returned unreadable data) -
        # save the raw bytes so a human can inspect why, and let the
        # deterministic check below report it properly.
        return {"image_bytes": raw_bytes, "format": None, "check_error": f"Could not process output image: {exc}"}

    try:
        image_format = validate_candidate(image_bytes, config.CANDIDATE_WIDTH, config.CANDIDATE_HEIGHT)
        check_error = None
    except ImageCheckError as exc:
        image_format = None
        check_error = str(exc)
    return {"image_bytes": image_bytes, "format": image_format, "check_error": check_error}


def generate_candidates(
    creative_brief: dict,
    product: dict,
    garment_reference: str,
    model_reference: str | None,
    num_candidates: int | None = None,
) -> dict:
    """Generates `num_candidates` (default config.NUM_CANDIDATES) fresh
    candidates, saves each plus one manifest.json under
    config.OUTPUT_DIR/<handle>_<run_id>/, and returns that manifest dict.
    """
    api_key = config.get_gemini_api_key()
    model = config.get_gemini_model()
    api_base = config.get_gemini_api_base()
    num_candidates = num_candidates or config.NUM_CANDIDATES

    prompt = build_prompt(creative_brief, product, model_reference)
    reference_images = [load_reference_bytes(garment_reference)]
    if model_reference:
        reference_images.append(load_reference_bytes(model_reference))

    run_id = uuid.uuid4().hex[:8]
    handle = product.get("handle", "product")
    run_dir = config.OUTPUT_DIR / f"{handle}_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for i in range(1, num_candidates + 1):
        result = _generate_one(prompt, reference_images, api_key, model, api_base)
        ext = result["format"] or "bin"
        output_path = run_dir / f"candidate_{i}.{ext}"
        output_path.write_bytes(result["image_bytes"])
        candidates.append({
            "index": i,
            "output_path": str(output_path),
            "format": result["format"],
            "passed_checks": result["check_error"] is None,
            "check_error": result["check_error"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    manifest = {
        "product": {
            "title": product.get("title"),
            "handle": product.get("handle"),
            "product_url": product.get("product_url"),
        },
        "prompt": prompt,
        "model": model,
        "garment_reference": garment_reference,
        "model_reference": model_reference,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidates": candidates,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def generate_one_more(run_dir: str) -> dict:
    """Manual retry: one additional candidate into an existing run,
    reusing that run's own saved prompt/references (a real retry, not a
    fresh creative direction)."""
    run_path = Path(run_dir)
    manifest_path = run_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    api_key = config.get_gemini_api_key()
    model = manifest["model"]
    api_base = config.get_gemini_api_base()
    reference_images = [load_reference_bytes(manifest["garment_reference"])]
    if manifest.get("model_reference"):
        reference_images.append(load_reference_bytes(manifest["model_reference"]))

    result = _generate_one(manifest["prompt"], reference_images, api_key, model, api_base)
    next_index = len(manifest["candidates"]) + 1
    ext = result["format"] or "bin"
    output_path = run_path / f"candidate_{next_index}.{ext}"
    output_path.write_bytes(result["image_bytes"])

    manifest["candidates"].append({
        "index": next_index,
        "output_path": str(output_path),
        "format": result["format"],
        "passed_checks": result["check_error"] is None,
        "check_error": result["check_error"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "retry": True,
    })
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest
