"""Wires config + client + normalizer into the output contract. One
synchronous request, no pagination - matches the small one-shot CLI batch
Sequence A already established."""
from ad_fetcher.scrapecreators_client import ScrapeCreatorsError

from . import config
from .normalizer import normalize_posts
from .scrapecreators_client import fetch_instagram_posts


def fetch_and_normalize() -> dict:
    api_key = config.get_api_key()
    raw = fetch_instagram_posts(
        api_key=api_key,
        handle=config.ACCOUNT_HANDLE,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )

    items = raw.get("items")
    if not isinstance(items, list):
        # Distinct from a genuinely empty batch (items: []) - the response
        # shape itself is wrong, so this is a provider error, not zero results.
        raise ScrapeCreatorsError(
            "ScrapeCreators response is missing a valid 'items' list."
        )

    posts = normalize_posts(
        items, brand=config.BRAND_LABEL, handle=config.ACCOUNT_HANDLE, platform=config.PLATFORM
    )
    return {"count": len(posts), "organic_posts": posts}
