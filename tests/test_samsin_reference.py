"""Sequence E, Part 2: Samsin reference fetcher. No live network - the
HTTP client is mocked/faked throughout, using fixtures shaped exactly like
the real live responses captured this session (products.json + the
storefront .js availability endpoint)."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from samsin_reference import config  # noqa: E402
from samsin_reference.catalog import build_tshirt_catalog, is_tshirt, normalize_product  # noqa: E402
from samsin_reference.client import SamsinFetchError  # noqa: E402
from samsin_reference.service import fetch_tshirt_catalog  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures_samsin"


def load(name):
    return json.loads((FIXTURES / name).read_text())


class KnownModelReferencesTests(unittest.TestCase):
    def test_star_t_shirt_radiostar_has_the_confirmed_official_model_reference(self):
        # Automatic model-photo classification is a documented future
        # improvement (Samsin's catalog has zero alt-text-tagged model
        # images) - this one product's override was manually confirmed
        # against the live storefront, not guessed.
        self.assertEqual(
            config.KNOWN_MODEL_REFERENCES["star-t-shirt-radiostar"],
            "https://shopsamsin.com/cdn/shop/files/big-star-min.png?v=1769512693",
        )


class IsTshirtTests(unittest.TestCase):
    def test_matches_on_title_or_product_type(self):
        self.assertTrue(is_tshirt({"title": "STAR T-SHIRT WHITE", "product_type": "Star T-Shirt"}))
        self.assertTrue(is_tshirt({"title": "Some Tee", "product_type": ""}))
        self.assertFalse(is_tshirt({"title": "OVERSIZED HOODIE", "product_type": "Hoodie"}))


class NormalizeProductTests(unittest.TestCase):
    def test_in_stock_product_with_model_and_garment_images(self):
        entries = load("products_list.json")["products"]
        star = next(p for p in entries if p["handle"] == "star-t-shirt-radiostar")
        detail = load("detail_star.json")

        record = normalize_product(star, detail)
        self.assertIsNotNone(record)
        self.assertEqual(record["title"], "STAR T-SHIRT WHITE")
        self.assertEqual(record["product_url"], "https://shopsamsin.com/products/star-t-shirt-radiostar")
        self.assertEqual(record["price"], 38.9)
        self.assertEqual(record["currency"], "USD")
        self.assertTrue(record["in_stock"])
        self.assertEqual(record["model_image_urls"], ["https://cdn.shopify.com/s/files/1/star-model.jpg"])
        self.assertEqual(
            record["garment_image_urls"],
            ["https://cdn.shopify.com/s/files/1/star-front.jpg", "https://cdn.shopify.com/s/files/1/star-back.jpg"],
        )
        self.assertEqual(len(record["all_image_urls"]), 3)

    def test_out_of_stock_is_never_reported_as_in_stock(self):
        entries = load("products_list.json")["products"]
        camo = next(p for p in entries if p["handle"] == "camo-t-shirt")
        detail = load("detail_camo.json")

        record = normalize_product(camo, detail)
        self.assertIsNotNone(record)
        self.assertFalse(record["in_stock"])

    def test_missing_available_field_is_null_not_invented_true(self):
        entries = load("products_list.json")["products"]
        camo = next(p for p in entries if p["handle"] == "camo-t-shirt")
        record = normalize_product(camo, {"price": 3490})  # no "available" key at all
        self.assertIsNotNone(record)
        self.assertIsNone(record["in_stock"])

    def test_product_with_no_images_is_rejected(self):
        entries = load("products_list.json")["products"]
        no_image = next(p for p in entries if p["handle"] == "no-image-tee")
        record = normalize_product(no_image, {"available": True, "price": 1000})
        self.assertIsNone(record)

    def test_missing_handle_is_rejected(self):
        record = normalize_product({"title": "X", "images": [{"src": "https://x/1.jpg"}]}, {"available": True})
        self.assertIsNone(record)

    def test_malformed_input_rejected(self):
        self.assertIsNone(normalize_product("not a dict", {}))
        self.assertIsNone(normalize_product({}, "not a dict"))


class BuildCatalogTests(unittest.TestCase):
    def test_restricted_to_tshirts_and_matches_details_by_handle(self):
        products = load("products_list.json")["products"]
        details = {
            "star-t-shirt-radiostar": load("detail_star.json"),
            "camo-t-shirt": load("detail_camo.json"),
            "no-image-tee": {"available": True, "price": 1000},
        }
        catalog = build_tshirt_catalog(products, lambda handle: details[handle])
        handles = {p["handle"] for p in catalog}
        self.assertEqual(handles, {"star-t-shirt-radiostar", "camo-t-shirt"})  # hoodie + no-image-tee excluded

    def test_service_wires_client_into_catalog(self):
        products = load("products_list.json")["products"]
        details = {
            "star-t-shirt-radiostar": load("detail_star.json"),
            "camo-t-shirt": load("detail_camo.json"),
            "no-image-tee": {"available": True, "price": 1000},
        }
        with mock.patch("samsin_reference.service.fetch_products_list", return_value=products):
            with mock.patch("samsin_reference.service.fetch_product_detail", side_effect=lambda h: details[h]):
                output = fetch_tshirt_catalog()
        self.assertEqual(output["count"], 2)


class ClientErrorTests(unittest.TestCase):
    def test_http_error_raises_samsin_fetch_error(self):
        import urllib.error

        with mock.patch(
            "samsin_reference.client.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None),
        ):
            with self.assertRaises(SamsinFetchError) as ctx:
                from samsin_reference.client import fetch_products_list

                fetch_products_list()
        self.assertIn("404", str(ctx.exception))

    def test_malformed_json_raises_samsin_fetch_error(self):
        response = mock.MagicMock()
        response.read.return_value = b"not json{"
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with mock.patch("samsin_reference.client.urllib.request.urlopen", return_value=response):
            from samsin_reference.client import fetch_products_list

            with self.assertRaises(SamsinFetchError):
                fetch_products_list()


if __name__ == "__main__":
    unittest.main()
