"""Wires config + client + normalizer into the one output contract.
Synchronous - this is a small one-shot CLI batch, not a background job."""
from . import config
from .normalizer import normalize_ads
from .scrapecreators_client import ScrapeCreatorsError, fetch_company_ads


def fetch_and_normalize() -> dict:
    api_key = config.get_api_key()
    raw = fetch_company_ads(
        api_key=api_key,
        page_id=config.COMPETITOR["page_id"],
        country=config.COUNTRY,
        media_type=config.PAID_MEDIA_TYPE,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )

    if not isinstance(raw, dict):
        # e.g. the provider returned a bare JSON list/string/number/null -
        # not the {"results": [...]} shape at all. Mirrors organic_fetcher's
        # equivalent check.
        raise ScrapeCreatorsError("ScrapeCreators response was not a JSON object.")

    results = raw.get("results")
    if not isinstance(results, list):
        # Distinct from a genuinely empty batch (results: []) - the response
        # shape itself is wrong, so this is a provider error, not zero results.
        raise ScrapeCreatorsError(
            "ScrapeCreators response is missing a valid 'results' list."
        )

    ads = normalize_ads(results, brand=config.BRAND_LABEL, limit=config.BATCH_SIZE)
    return {"count": len(ads), "ads": ads}
