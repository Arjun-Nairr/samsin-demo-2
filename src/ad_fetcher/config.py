"""Central config: the one hardcoded competitor, API key, batch size.

No registry/factory/config-framework - there is exactly one competitor for
Sequence A and it lives here as one dict.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# ScrapeCreators' Company Ads endpoint accepts companyName directly (see
# docs.scrapecreators.com/v1/facebook/adlibrary/company/ads) so no
# company-search resolution call is needed for Sequence A. If a pageId is
# ever verified via the search endpoint, swap it in here instead of
# companyName - the client accepts either.
COMPETITOR = {
    "company_name": "Aelfric Eden",
}

BRAND_LABEL = "Aelfric Eden"

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
