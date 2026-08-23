"""Wires client + catalog into the one output contract. One product-list
request plus one detail request per T-shirt found - small, since the demo
catalog is restricted to T-shirts only (~7 products on the real store)."""
from .catalog import build_tshirt_catalog
from .client import fetch_product_detail, fetch_products_list


def fetch_tshirt_catalog() -> dict:
    products = fetch_products_list()
    catalog = build_tshirt_catalog(products, fetch_product_detail)
    return {"count": len(catalog), "products": catalog}
