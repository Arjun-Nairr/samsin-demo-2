"""Sequence E, Part 2: Samsin's own public storefront, fetched fresh.

Deliberately independent of the old samsin-pricing-demo project - no
import, no shared code, no reused local assets. Everything here comes
from Samsin's live public Shopify endpoints, inspected directly this
session (not assumed from prior knowledge of that project).
"""
BASE_URL = "https://shopsamsin.com"

# Demo catalog is restricted to T-shirts - matched on product_type or
# title, since Samsin's own product_type values are inconsistent
# ("T-Shirt" vs "Star T-Shirt" etc. - confirmed live).
TSHIRT_KEYWORDS = ("t-shirt", "tee")

REQUEST_TIMEOUT_SECONDS = 15

# Best-effort heuristic only (see catalog.py) - an image's alt text
# containing one of these is classified as a model/on-body reference.
# Samsin's live catalog was checked and currently has none at all (pure
# flat-lay photography); this list exists for when/if that changes, not
# because it's been observed working here.
MODEL_IMAGE_ALT_KEYWORDS = ("model", "wearing", "on-body", "on body", "lifestyle")
