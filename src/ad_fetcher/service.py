"""Wires config + client + normalizer into the one output contract.
Synchronous - this is a small one-shot CLI batch, not a background job."""
from . import config
from .normalizer import normalize_ads
from .scrapecreators_client import fetch_company_ads


def fetch_and_normalize() -> dict:
    api_key = config.get_api_key()
    raw = fetch_company_ads(
        api_key=api_key,
        company_name=config.COMPETITOR["company_name"],
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    results = raw.get("results") or []
    ads = normalize_ads(results, brand=config.BRAND_LABEL, limit=config.BATCH_SIZE)
    return {"count": len(ads), "ads": ads}
