"""Isolated ScrapeCreators HTTP call. Nothing else in the codebase should
know this is an HTTP request - normalizer.py works on plain dicts so
swapping providers later stays a one-file change.

Uses urllib (stdlib) instead of adding `requests` for one GET request.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.scrapecreators.com"
ADS_PATH = "/v1/facebook/adLibrary/company/ads"

# One bounded retry: only for transient/network failures, not for 4xx
# (auth/bad-request) errors which won't fix themselves on retry.
_MAX_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 2


class ScrapeCreatorsError(Exception):
    """Raised for any provider failure. Message is safe to print - never
    includes the API key."""


def fetch_company_ads(api_key: str, company_name: str, timeout: int) -> dict:
    """GET the Company Ads endpoint for one company. Returns the parsed
    JSON response body. Raises ScrapeCreatorsError on any failure.
    """
    if not api_key:
        raise ScrapeCreatorsError(
            "Missing SCRAPECREATORS_API_KEY. Set it in .env or the "
            "environment before running."
        )

    params = urllib.parse.urlencode(
        {
            "companyName": company_name,
            "country": "ALL",
            "status": "ACTIVE",
        }
    )
    url = f"{API_BASE}{ADS_PATH}?{params}"
    request = urllib.request.Request(url, headers={"x-api-key": api_key})

    last_error = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                raise ScrapeCreatorsError(
                    f"ScrapeCreators returned malformed JSON: {exc}"
                ) from exc

        except urllib.error.HTTPError as exc:
            # Auth/bad-request errors are not transient - fail immediately,
            # never echo the key (it's a header, not in the body/URL logged).
            if exc.code in (401, 403):
                raise ScrapeCreatorsError(
                    f"ScrapeCreators authentication failed (HTTP {exc.code}). "
                    "Check SCRAPECREATORS_API_KEY."
                ) from exc
            last_error = ScrapeCreatorsError(
                f"ScrapeCreators returned HTTP {exc.code}."
            )
        except urllib.error.URLError as exc:
            last_error = ScrapeCreatorsError(
                f"ScrapeCreators request failed: {exc.reason}"
            )
        except TimeoutError:
            last_error = ScrapeCreatorsError(
                f"ScrapeCreators request timed out after {timeout}s."
            )

        if attempt < _MAX_ATTEMPTS:
            time.sleep(_RETRY_DELAY_SECONDS)

    raise last_error
