"""Covers the deterministic cleanup rules against realistic fixtures matching
the documented ScrapeCreators Company Ads schema. stdlib unittest - no
pytest dependency added for this."""
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ad_fetcher.normalizer import normalize_ad, normalize_ads  # noqa: E402
from ad_fetcher.scrapecreators_client import (  # noqa: E402
    ScrapeCreatorsError,
    fetch_company_ads,
)

FIXTURES = Path(__file__).parent / "fixtures"
BRAND = "Aelfric Eden"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


class NormalizeOneAdTests(unittest.TestCase):
    def test_valid_image_ad(self):
        record = normalize_ad(load("image_ad.json"), BRAND)
        self.assertIsNotNone(record)
        self.assertEqual(record["ad_id"], "111111111111111")
        self.assertEqual(record["brand"], BRAND)
        self.assertEqual(record["body"], "New drop: oversized graphic tees.")  # trimmed
        self.assertEqual(record["media_type"], "image")
        self.assertEqual(record["media_url"], "https://scontent.xx.fbcdn.net/ad-image-1.jpg")
        self.assertEqual(record["cta"], "Shop Now")
        self.assertTrue(record["is_active"])
        self.assertEqual(record["started_at"], "2025-06-15T15:06:40+00:00")
        self.assertEqual(
            record["snapshot_url"], "https://www.facebook.com/ads/library/?id=111111111111111"
        )

    def test_valid_video_ad(self):
        record = normalize_ad(load("video_ad.json"), BRAND)
        self.assertIsNotNone(record)
        self.assertEqual(record["media_type"], "video")
        self.assertEqual(record["media_url"], "https://video.xx.fbcdn.net/ad-video-hd.mp4")

    def test_carousel_uses_first_card_deterministically(self):
        record = normalize_ad(load("carousel_ad.json"), BRAND)
        self.assertIsNotNone(record)
        self.assertEqual(record["headline"], "Cropped Hoodie")
        self.assertEqual(record["body"], "Card 1: cropped hoodie, 4 colorways.")
        self.assertEqual(record["media_url"], "https://scontent.xx.fbcdn.net/card-1.jpg")
        self.assertFalse(record["is_active"])

    def test_missing_media_rejected(self):
        self.assertIsNone(normalize_ad(load("missing_media.json"), BRAND))

    def test_unsupported_media_type_rejected(self):
        self.assertIsNone(normalize_ad(load("unsupported_media.json"), BRAND))

    def test_missing_ad_id_rejected(self):
        self.assertIsNone(normalize_ad(load("missing_id.json"), BRAND))

    def test_malformed_record_rejected(self):
        self.assertIsNone(normalize_ad(load("malformed.json"), BRAND))

    def test_video_uses_first_valid_candidate_when_earlier_ones_are_bad(self):
        record = normalize_ad(load("video_ad_later_candidate.json"), BRAND)
        self.assertIsNotNone(record)
        self.assertEqual(
            record["media_url"], "https://video.xx.fbcdn.net/ad-video-later-candidate-hd.mp4"
        )

    def test_image_uses_first_valid_candidate_when_earlier_ones_are_bad(self):
        record = normalize_ad(load("image_ad_later_candidate.json"), BRAND)
        self.assertIsNotNone(record)
        self.assertEqual(
            record["media_url"], "https://scontent.xx.fbcdn.net/ad-image-later-candidate.jpg"
        )

    def test_boolean_start_date_rejected_not_treated_as_timestamp(self):
        record = normalize_ad(load("boolean_start_date.json"), BRAND)
        self.assertIsNotNone(record)  # ad itself is still valid, just no date
        self.assertIsNone(record["started_at"])


class NormalizeAdsListTests(unittest.TestCase):
    def test_deduplicates_keeping_first_valid(self):
        raw = [load("image_ad.json"), load("duplicate_ad.json")]
        ads = normalize_ads(raw, BRAND, limit=20)
        self.assertEqual(len(ads), 1)
        self.assertEqual(ads[0]["body"], "New drop: oversized graphic tees.")

    def test_filters_and_preserves_order(self):
        raw = [
            load("image_ad.json"),
            load("malformed.json"),
            load("missing_id.json"),
            load("unsupported_media.json"),
            load("missing_media.json"),
            load("video_ad.json"),
            load("carousel_ad.json"),
            load("duplicate_ad.json"),
        ]
        ads = normalize_ads(raw, BRAND, limit=20)
        self.assertEqual([a["ad_id"] for a in ads], ["111111111111111", "444444444444444", "666666666666666"])

    def test_empty_results(self):
        raw = load("empty_results.json")
        ads = normalize_ads(raw["results"], BRAND, limit=20)
        self.assertEqual(ads, [])

    def test_limit_is_respected(self):
        raw = [load("image_ad.json"), load("video_ad.json"), load("carousel_ad.json")]
        ads = normalize_ads(raw, BRAND, limit=2)
        self.assertEqual(len(ads), 2)


class ProviderErrorMessageTests(unittest.TestCase):
    def test_missing_key_raises_without_making_a_request(self):
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_company_ads(api_key="", company_name=BRAND, timeout=5)
        self.assertIn("SCRAPECREATORS_API_KEY", str(ctx.exception))

    def test_error_messages_never_contain_the_key_value(self):
        # scrapecreators_client only ever puts the key in the request header,
        # never interpolates it into an exception message - assert that
        # invariant directly against the source rather than a live network
        # call (offline, deterministic).
        source = Path(__file__).resolve().parent.parent / "src" / "ad_fetcher" / "scrapecreators_client.py"
        text = source.read_text()
        for line in text.splitlines():
            if "raise ScrapeCreatorsError" in line or ("f\"" in line and "ScrapeCreators" in line):
                self.assertNotIn("api_key", line)


SECRET_KEY = "sk_test_should_never_appear_anywhere"


class ProviderErrorBehaviorTests(unittest.TestCase):
    """Behavioral (mocked, no live requests/credits) checks that actual
    raised error messages are sane and never contain the real key value -
    supplements the source-scan test above with what really happens at
    runtime for each failure mode."""

    @mock.patch("ad_fetcher.scrapecreators_client.time.sleep")
    @mock.patch("ad_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_auth_failure_message_and_no_key_leak(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, None
        )
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_company_ads(api_key=SECRET_KEY, company_name=BRAND, timeout=5)
        self.assertIn("401", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))

    @mock.patch("ad_fetcher.scrapecreators_client.time.sleep")
    @mock.patch("ad_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_non_auth_http_error_message_and_no_key_leak(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 500, "Internal Server Error", {}, None
        )
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_company_ads(api_key=SECRET_KEY, company_name=BRAND, timeout=5)
        self.assertIn("500", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))

    @mock.patch("ad_fetcher.scrapecreators_client.time.sleep")
    @mock.patch("ad_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_timeout_message_and_no_key_leak(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = TimeoutError()
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_company_ads(api_key=SECRET_KEY, company_name=BRAND, timeout=5)
        self.assertIn("timed out", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))

    @mock.patch("ad_fetcher.scrapecreators_client.time.sleep")
    @mock.patch("ad_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_network_error_message_and_no_key_leak(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = urllib.error.URLError("no route to host")
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_company_ads(api_key=SECRET_KEY, company_name=BRAND, timeout=5)
        self.assertIn("no route to host", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))

    @mock.patch("ad_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_malformed_json_message_and_no_key_leak(self, mock_urlopen):
        response = mock.MagicMock()
        response.read.return_value = b"not json{"
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        mock_urlopen.return_value = response

        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_company_ads(api_key=SECRET_KEY, company_name=BRAND, timeout=5)
        self.assertIn("malformed JSON", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
