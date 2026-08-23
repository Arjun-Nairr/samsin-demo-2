"""Sequence B config: the one hardcoded Instagram account.

Reuses ad_fetcher's .env/API-key loading directly rather than duplicating
it - it's provider-agnostic (just reads SCRAPECREATORS_API_KEY), so there's
nothing Sequence-A-specific about it.

Sequence D: identity updated to the verified PacSun account
(ig_username "pacsun", BLUE_VERIFIED, 2,678,292 followers - confirmed via
the same company-search lookup that verified ad_fetcher's page ID; see
ad_fetcher/config.py). Sequence B's own logic is unchanged - identity only.
"""
from ad_fetcher.config import get_api_key  # noqa: F401  (re-exported for callers)

PLATFORM = "instagram"
ACCOUNT_HANDLE = "pacsun"
BRAND_LABEL = "PacSun"

REQUEST_TIMEOUT_SECONDS = 15
