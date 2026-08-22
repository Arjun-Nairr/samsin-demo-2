"""Deterministic cleanup only: no AI, no fuzzy matching. Pure functions
over plain dicts.

Real-schema notes (confirmed against a live `trim=true` response, not
guessed from docs):
- `pk` is always null under trim=true. `id` (a stable composite string,
  e.g. "3954222268720362185_11087474383") is the real stable post ID.
- The API already returns a full permalink at `url` for every observed
  item (including reels, which still use the `/p/<code>/` form, not
  `/reel/...`). Shortcode construction is fallback-only.
- Inside a carousel, each `carousel_media[]` entry has its own
  `media_type`/`video_versions`/`image_versions2`, but NONE of them carry
  `play_count`/`like_count`/`comment_count` - those only exist on the
  container item. So: media is resolved from the selected item (container
  itself, or the first supported carousel sub-item); engagement metrics
  always come from the top-level item.
- Video items also carry `image_versions2` (the poster frame) - that's
  `thumbnail_url`. Image items have no separate thumbnail; media_url IS
  the image, so thumbnail_url stays null there (no point duplicating it).
"""
from datetime import datetime, timezone

MEDIA_TYPE_KIND = {1: "image", 2: "video"}
CAROUSEL_CONTAINER = 8


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _is_http_url(value) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _first_http_url(*candidates):
    for candidate in candidates:
        if _is_http_url(candidate):
            return candidate
    return None


def _image_url(image_versions2) -> str | None:
    candidates = (image_versions2 or {}).get("candidates") or []
    first = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
    return _first_http_url(first.get("url"))


def _resolve_single_media(node: dict) -> dict | None:
    """node is either the top-level item or one carousel_media[] entry."""
    kind = MEDIA_TYPE_KIND.get(node.get("media_type"))
    if kind is None:
        return None  # unsupported media type

    if kind == "video":
        versions = node.get("video_versions") or []
        first = versions[0] if versions and isinstance(versions[0], dict) else {}
        media_url = _first_http_url(first.get("url"))
        if not media_url:
            return None
        return {
            "post_type": "video",
            "media_url": media_url,
            "thumbnail_url": _image_url(node.get("image_versions2")),
        }

    media_url = _image_url(node.get("image_versions2"))
    if not media_url:
        return None
    return {"post_type": "image", "media_url": media_url, "thumbnail_url": None}


def _resolve_media(item: dict) -> dict | None:
    if item.get("media_type") == CAROUSEL_CONTAINER:
        for sub in item.get("carousel_media") or []:
            if isinstance(sub, dict):
                resolved = _resolve_single_media(sub)
                if resolved:
                    return resolved  # first supported item, deterministically
        return None  # no supported media in the carousel
    return _resolve_single_media(item)


def _int_or_none(value):
    """Preserves a real 0; only non-numeric/missing becomes None."""
    if isinstance(value, bool):
        return None  # bool is technically an int subclass - not a real count
    return value if isinstance(value, int) else None


def normalize_post(raw: object, brand: str, handle: str, platform: str) -> dict | None:
    if not isinstance(raw, dict):
        return None  # reject non-object/malformed records

    post_id = raw.get("id")
    if not isinstance(post_id, str) or not post_id.strip():
        return None  # reject records without a stable post ID

    media = _resolve_media(raw)
    if media is None:
        return None  # reject unsupported types / records without usable media

    code = _text(raw.get("code"))
    caption_obj = raw.get("caption")
    caption = _text(caption_obj.get("text")) if isinstance(caption_obj, dict) else ""

    taken_at = raw.get("taken_at")
    published_at = None
    if isinstance(taken_at, (int, float)):
        published_at = datetime.fromtimestamp(taken_at, tz=timezone.utc).isoformat()

    permalink = _first_http_url(raw.get("url"))
    if not permalink and code:
        permalink = f"https://www.instagram.com/p/{code}/"

    # Instagram-specific play count preferred over the generic one, per spec.
    view_count = _int_or_none(raw.get("ig_play_count"))
    if view_count is None:
        view_count = _int_or_none(raw.get("play_count"))

    return {
        "platform": platform,
        "post_id": post_id,
        "shortcode": code,
        "brand": brand,
        "account_handle": handle,
        "post_type": media["post_type"],
        "caption": caption,
        "published_at": published_at,
        "permalink": permalink,
        "media_url": media["media_url"],
        "thumbnail_url": media["thumbnail_url"],
        "organic_view_count": view_count,
        "organic_like_count": _int_or_none(raw.get("like_count")),
        "organic_comment_count": _int_or_none(raw.get("comment_count")),
    }


def normalize_posts(raw_items: list, brand: str, handle: str, platform: str) -> list:
    """Normalize, reject, and dedupe by (platform, post_id) - first valid
    wins. Preserves provider order. No ranking/sorting, no limit (one
    request, no pagination - whatever the API returns is the whole batch)."""
    seen = set()
    normalized = []
    for raw in raw_items or []:
        record = normalize_post(raw, brand, handle, platform)
        if record is None:
            continue
        key = (record["platform"], record["post_id"])
        if key in seen:
            continue
        seen.add(key)
        normalized.append(record)
    return normalized
