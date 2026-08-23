"""Sequence B config: the one hardcoded Instagram account.

Reuses ad_fetcher's .env/API-key loading directly rather than duplicating
it - it's provider-agnostic (just reads SCRAPECREATORS_API_KEY), so there's
nothing Sequence-A-specific about it.

Competitor changed (post-Sequence-E): PacSun replaced with Billionaire Boys
Club Icecream - see ad_fetcher/config.py for why. Sequence B's own logic is
unchanged - identity only. The Instagram handle below has not been
independently re-verified via company-search this session (same caveat as
before: identity is asserted, not cross-checked against a returned
page_id/URL) - flagging this rather than overclaiming verification.
"""
from ad_fetcher.config import get_api_key  # noqa: F401  (re-exported for callers)

PLATFORM = "instagram"
ACCOUNT_HANDLE = "bbcicecream"
BRAND_LABEL = "Billionaire Boys Club Icecream"

REQUEST_TIMEOUT_SECONDS = 15
