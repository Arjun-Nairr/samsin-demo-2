"""Isolated HTTP calls to Samsin's public Shopify storefront. Nothing else
in this package should know these are plain unauthenticated GETs -
catalog.py works on the parsed dicts this returns.

Two endpoints, both public/unauthenticated (no API key - this is just
reading a public website, not a paid provider):
- /products.json           - list + per-image alt text (weaker on
                              availability - many stores omit it here)
- /products/<handle>.js    - one product's real, reliable per-variant
                              `available`/`price` (Shopify's storefront
                              AJAX endpoint - confirmed live to return
                              accurate availability where products.json
                              did not).
"""
import json
import urllib.error
import urllib.request

from .config import BASE_URL, REQUEST_TIMEOUT_SECONDS

_HEADERS = {"User-Agent": "Mozilla/5.0 (samsin-ad-intelligence reference fetcher)"}


class SamsinFetchError(Exception):
    """Raised for any failure fetching Samsin's public storefront."""


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SamsinFetchError(f"Samsin storefront returned HTTP {exc.code} for {url}.") from exc
    except urllib.error.URLError as exc:
        raise SamsinFetchError(f"Samsin storefront request failed: {exc.reason}") from exc
    except TimeoutError:
        raise SamsinFetchError(f"Samsin storefront request timed out after {REQUEST_TIMEOUT_SECONDS}s.")

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SamsinFetchError(f"Samsin storefront returned malformed JSON: {exc}") from exc


def fetch_products_list() -> list:
    """The public product listing - includes per-image alt text but not
    always reliable availability (confirmed live: this store's variants
    omit `available` here entirely)."""
    body = _get_json(f"{BASE_URL}/products.json?limit=250")
    products = body.get("products")
    return products if isinstance(products, list) else []


def fetch_product_detail(handle: str) -> dict:
    """The storefront AJAX endpoint - real, reliable `available`/`price`
    per variant, confirmed live against this store."""
    return _get_json(f"{BASE_URL}/products/{handle}.js")
