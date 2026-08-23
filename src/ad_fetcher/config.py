"""Central config: the one hardcoded competitor, API key, batch size.

No registry/factory/config-framework - there is exactly one competitor for
Sequence A and it lives here as one dict.

Competitor changed (post-Sequence-E): PacSun was confirmed twice, live, to
have ~0 usable static image/meme ads (100% DCO/video even with status=ALL
and a 60-day window) - see HANDOFF.md "Sequence E, Part 1". Replaced with
Billionaire Boys Club Icecream, Meta page ID 142427132456114, verified by
a live diagnostic fetch that found 16 usable active US static-image ads.

Prior verified identity (Sequence D, superseded): PacSun, page_id
7133041750, resolved via ScrapeCreators' company-search endpoint - see git
history for that note if needed.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Fetch by the verified Meta page ID directly, not a fuzzy companyName
# lookup - see the verification note above.
COMPETITOR = {
    "name": "Billionaire Boys Club Icecream",
    "page_id": "142427132456114",
}

BRAND_LABEL = "Billionaire Boys Club Icecream"

# Sequence D: the paid-ad output contract is now static-image-only, filtered
# server-side too (see scrapecreators_client.py) - not just a defensive
# normalizer check.
COUNTRY = "US"
PAID_MEDIA_TYPE = "IMAGE_AND_MEME"

# Small useful batch per the spec - not a full crawl, no pagination.
BATCH_SIZE = 20

REQUEST_TIMEOUT_SECONDS = 15


def load_env() -> dict:
    """Minimal .env parser (KEY=VALUE per line). No python-dotenv dependency
    added for a single key."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k] = v.strip()
    return env


def get_api_key() -> str | None:
    """Env var wins over .env, matching normal shell-override expectations."""
    import os

    return os.environ.get("SCRAPECREATORS_API_KEY") or load_env().get(
        "SCRAPECREATORS_API_KEY"
    )
