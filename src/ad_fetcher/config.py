"""Central config: the one hardcoded competitor, API key, batch size.

No registry/factory/config-framework - there is exactly one competitor for
Sequence A and it lives here as one dict.

Verified competitor identity (Sequence D): resolved via ScrapeCreators'
company-search endpoint, not guessed. The top result for query="pacsun"
was unambiguously the official account - BLUE_VERIFIED on both platforms,
2,256,162 Facebook likes, 2,678,292 Instagram followers, page_alias
"pacsun", ig_username "pacsun" - clearly distinguished from several
unrelated/fan-page results also named "Pacsun" in the same search. Cross-
checked against the URLs the user gave (facebook.com/pacsun,
instagram.com/pacsun) before being locked in here.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Sequence D: fetch by the verified Meta page ID directly, not a fuzzy
# companyName lookup - see the verification note above.
COMPETITOR = {
    "name": "PacSun",
    "page_id": "7133041750",
}

BRAND_LABEL = "PacSun"

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
