"""Isolated ScrapeCreators HTTP call for Instagram Posts. Mirrors
ad_fetcher/scrapecreators_client.py's retry/error shape (imports its
API_BASE and ScrapeCreatorsError rather than duplicating the constant/type)
but is not merged into one shared client - the two endpoints have
different params and response shapes, and Sequence A must stay untouched.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from ad_fetcher.scrapecreators_client import API_BASE, ScrapeCreatorsError

POSTS_PATH = "/v2/instagram/user/posts"

_MAX_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 2


def fetch_instagram_posts(api_key: str, handle: str, timeout: int) -> dict:
    """GET the Instagram Posts endpoint for one account, trimmed. Returns
    the parsed JSON response body. Raises ScrapeCreatorsError on failure.
    """
    if not api_key:
        raise ScrapeCreatorsError(
            "Missing SCRAPECREATORS_API_KEY. Set it in .env or the "
            "environment before running."
        )

    params = urllib.parse.urlencode({"handle": handle, "trim": "true"})
    url = f"{API_BASE}{POSTS_PATH}?{params}"
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
