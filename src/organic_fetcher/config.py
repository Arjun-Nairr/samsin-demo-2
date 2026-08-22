"""Sequence B config: the one hardcoded Instagram account.

Reuses ad_fetcher's .env/API-key loading directly rather than duplicating
it - it's provider-agnostic (just reads SCRAPECREATORS_API_KEY), so there's
nothing Sequence-A-specific about it.
"""
from ad_fetcher.config import get_api_key  # noqa: F401  (re-exported for callers)

PLATFORM = "instagram"
ACCOUNT_HANDLE = "aelfricedenofficial"
BRAND_LABEL = "Aelfric Eden"

REQUEST_TIMEOUT_SECONDS = 15
