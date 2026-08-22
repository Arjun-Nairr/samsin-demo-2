"""Deterministic cleanup only: no AI, no fuzzy matching, no content
analysis. Pure functions over plain dicts - independent of HTTP details so
this file doesn't change if the provider changes.

Primary-asset rule for carousel/DCO ads (cards[]): use cards[0] as the one
deterministic primary creative, falling back to the top-level snapshot
fields for anything the card itself doesn't set. We do not expand one ad
into multiple records.

Missing values are `None` (JSON null) for non-text fields and `""` for text
fields, never invented.
"""
from datetime import datetime, timezone

SUPPORTED_MEDIA = {
    "VIDEO": "video",
    "IMAGE": "image",
    "MEME": "image",  # a MEME is an image variant per the documented schema
}


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_http_url(*candidates) -> str | None:
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
            return candidate
    return None


def _resolve_creative(snapshot: dict) -> dict:
    """Picks the primary card (if a carousel) or the top-level snapshot
    itself, and extracts body/headline/cta/media from it."""
    cards = snapshot.get("cards") or []
    primary = cards[0] if cards and isinstance(cards[0], dict) else {}

    body = _text((primary.get("body") if isinstance(primary.get("body"), str) else None)) \
        or _text((snapshot.get("body") or {}).get("text") if isinstance(snapshot.get("body"), dict) else None)
    headline = _text(primary.get("title")) or _text(snapshot.get("title"))
    cta = _text(primary.get("cta_text")) or _text(snapshot.get("cta_text"))

    display_format = snapshot.get("display_format")
    media_type = SUPPORTED_MEDIA.get(display_format)

    media_url = None
    if media_type == "video":
        videos = primary.get("videos") or snapshot.get("videos") or []
        # Scan every candidate, not just the first - a malformed/URL-less
        # first entry shouldn't hide a valid one further down the list.
        for video in videos:
            if not isinstance(video, dict):
                continue
            media_url = _first_http_url(video.get("video_hd_url"), video.get("video_sd_url"))
            if media_url:
                break
    elif media_type == "image":
        images = primary.get("images") or snapshot.get("images") or []
        # Real responses use original_image_url/resized_image_url, not the
        # "url" key shown in the docs' example - confirmed against a live
        # fetch. original_image_url preferred (full quality) over resized.
        for image in images:
            if not isinstance(image, dict):
                continue
            media_url = _first_http_url(
                image.get("url"), image.get("original_image_url"), image.get("resized_image_url")
            )
            if media_url:
                break

    return {
        "body": body,
        "headline": headline,
        "cta": cta,
        "media_type": media_type,
        "media_url": media_url,
    }


def normalize_ad(raw: object, brand: str) -> dict | None:
    """Returns a normalized record, or None if the record must be rejected."""
    if not isinstance(raw, dict):
        return None  # reject non-object/malformed records

    ad_id = raw.get("ad_archive_id")
    if not isinstance(ad_id, str) or not ad_id.strip():
        return None  # reject records without a valid advertisement ID

    snapshot = raw.get("snapshot")
    if not isinstance(snapshot, dict):
        return None  # no creative to normalize -> no usable media

    creative = _resolve_creative(snapshot)
    if creative["media_type"] is None:
        return None  # reject unsupported media types
    if not creative["media_url"]:
        return None  # reject records without a usable http/https media URL

    start_date = raw.get("start_date")
    started_at = None
    # bool is a subclass of int - exclude it, or "start_date": true would
    # normalize to a bogus 1970-01-01T00:00:01Z instead of being rejected.
    if isinstance(start_date, (int, float)) and not isinstance(start_date, bool):
        started_at = datetime.fromtimestamp(start_date, tz=timezone.utc).isoformat()

    is_active = raw.get("is_active")
    is_active = bool(is_active) if isinstance(is_active, bool) else None

    # No dedicated permalink field is documented in the API response; this
    # is Meta's own public, stable Ad Library URL format built from the ID
    # ScrapeCreators returns - not a guessed or fabricated value.
    snapshot_url = f"https://www.facebook.com/ads/library/?id={ad_id}"

    return {
        "ad_id": ad_id,
        "brand": brand,
        "body": creative["body"],
        "headline": creative["headline"],
        "cta": creative["cta"],
        "media_type": creative["media_type"],
        "media_url": creative["media_url"],
        "started_at": started_at,
        "is_active": is_active,
        "snapshot_url": snapshot_url,
    }


def normalize_ads(raw_results: list, brand: str, limit: int) -> list:
    """Normalize, reject, and dedupe (first-valid-wins), preserving
    provider order, capped at `limit`."""
    seen_ids = set()
    normalized = []
    for raw in raw_results or []:
        record = normalize_ad(raw, brand)
        if record is None:
            continue
        if record["ad_id"] in seen_ids:
            continue  # duplicate ID -> keep the first valid record
        seen_ids.add(record["ad_id"])
        normalized.append(record)
        if len(normalized) >= limit:
            break
    return normalized
