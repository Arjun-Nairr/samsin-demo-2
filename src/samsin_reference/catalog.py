"""Deterministic normalization only - no AI, no vision, no guessing. Pure
functions over the two raw dicts client.py returns. Mirrors ad_fetcher's
normalizer.py pattern: reject what's unusable, never invent a value.

Image classification (garment vs. model/on-body) is a documented best-
effort heuristic based on the alt text Shopify merchants set, not a
guarantee. Every product also carries `all_image_urls` unfiltered, so no
image is ever lost even if the heuristic misses. Live-checked: Samsin's
current catalog is pure flat-lay photography with no alt text signaling a
model shot anywhere - `model_image_urls` is `[]` for every real product
right now. That's not a bug in the heuristic; it's what's actually there.
"""
from .config import MODEL_IMAGE_ALT_KEYWORDS, TSHIRT_KEYWORDS

BASE_URL = "https://shopsamsin.com"


def is_tshirt(product: dict) -> bool:
    title = (product.get("title") or "").lower()
    product_type = (product.get("product_type") or "").lower()
    return any(k in title or k in product_type for k in TSHIRT_KEYWORDS)


def _is_model_image(alt_text) -> bool:
    if not isinstance(alt_text, str):
        return False
    lowered = alt_text.lower()
    return any(keyword in lowered for keyword in MODEL_IMAGE_ALT_KEYWORDS)


def normalize_product(list_entry: dict, detail: dict) -> dict | None:
    """`list_entry` is one item from /products.json (has image alt text);
    `detail` is that same product's /products/<handle>.js response (has
    real availability/price). Returns None if the record is unusable."""
    if not isinstance(list_entry, dict) or not isinstance(detail, dict):
        return None

    handle = list_entry.get("handle")
    title = list_entry.get("title")
    if not isinstance(handle, str) or not handle.strip() or not isinstance(title, str) or not title.strip():
        return None  # can't build a real product URL / identify the product

    price_cents = detail.get("price")
    price = round(price_cents / 100, 2) if isinstance(price_cents, int) else None

    # Never invented: only a real boolean from the storefront counts as
    # known stock status; anything else stays null (unknown), not True.
    available = detail.get("available")
    in_stock = available if isinstance(available, bool) else None

    all_image_urls, garment_image_urls, model_image_urls = [], [], []
    for image in list_entry.get("images") or []:
        if not isinstance(image, dict):
            continue
        url = image.get("src")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        all_image_urls.append(url)
        if _is_model_image(image.get("alt")):
            model_image_urls.append(url)
        else:
            garment_image_urls.append(url)

    if not all_image_urls:
        return None  # no usable image - nothing to generate a creative from

    return {
        "title": title.strip(),
        "handle": handle,
        "product_url": f"{BASE_URL}/products/{handle}",
        "price": price,
        "currency": "USD",  # inferred from the store's USD-formatted pricing, not an explicit API field
        "in_stock": in_stock,
        "garment_image_urls": garment_image_urls,
        "model_image_urls": model_image_urls,
        "all_image_urls": all_image_urls,
    }


def build_tshirt_catalog(products: list, detail_fetcher) -> list:
    """`detail_fetcher(handle) -> dict` is injected so tests can fake it
    without a real HTTP call. Restricts to T-shirts, normalizes each,
    drops unusable records - deterministic, no fabrication."""
    catalog = []
    for product in products or []:
        if not isinstance(product, dict) or not is_tshirt(product):
            continue
        handle = product.get("handle")
        if not isinstance(handle, str) or not handle.strip():
            continue
        detail = detail_fetcher(handle)
        record = normalize_product(product, detail)
        if record is not None:
            catalog.append(record)
    return catalog
