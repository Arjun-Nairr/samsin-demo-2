"""Sequence B: deterministic cleanup against fixtures matching the real
(live-verified) ScrapeCreators Instagram Posts schema. stdlib unittest,
same pattern as tests/test_normalizer.py."""
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ad_fetcher.scrapecreators_client import ScrapeCreatorsError  # noqa: E402
from organic_fetcher.normalizer import normalize_post, normalize_posts  # noqa: E402
from organic_fetcher.scrapecreators_client import fetch_instagram_posts  # noqa: E402
from organic_fetcher.service import fetch_and_normalize  # noqa: F401,E402

FIXTURES = Path(__file__).parent / "fixtures_organic"
BRAND = "Aelfric Eden"
HANDLE = "aelfricedenofficial"
PLATFORM = "instagram"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def norm(name: str):
    return normalize_post(load(name), BRAND, HANDLE, PLATFORM)


class NormalizeOnePostTests(unittest.TestCase):
    def test_valid_image_post(self):
        record = norm("image_post.json")
        self.assertIsNotNone(record)
        self.assertEqual(record["post_type"], "image")
        self.assertEqual(record["media_url"], "https://scontent.cdninstagram.com/v/image-post-1.jpg?sig=abc...")
        self.assertIsNone(record["thumbnail_url"])  # redundant with media_url for images
        self.assertIsNone(record["organic_view_count"])  # images normally have no view count
        self.assertEqual(record["caption"], "New arrivals in-store now.")  # trimmed
        self.assertEqual(record["platform"], "instagram")
        self.assertEqual(record["account_handle"], HANDLE)

    def test_valid_video_reel(self):
        record = norm("video_post.json")
        self.assertIsNotNone(record)
        self.assertEqual(record["post_type"], "video")
        self.assertEqual(record["post_id"], "3954222268720362185_11087474383")
        self.assertEqual(record["media_url"], "https://scontent-atl3-1.cdninstagram.com/o1/v/t2/reel-1.mp4?sig=abc...")
        self.assertEqual(record["thumbnail_url"], "https://scontent-atl3-1.cdninstagram.com/v/thumb-video-1.jpg?sig=abc...")
        self.assertEqual(record["organic_view_count"], 123483)  # ig_play_count preferred
        self.assertEqual(record["permalink"], "https://www.instagram.com/p/DbgODP6BDLJ/")
        self.assertEqual(record["published_at"], "2026-08-01T16:00:08+00:00")

    def test_carousel_uses_first_supported_item_image(self):
        record = norm("carousel_post.json")
        self.assertIsNotNone(record)
        self.assertEqual(record["post_type"], "image")
        self.assertEqual(record["media_url"], "https://scontent.cdninstagram.com/v/card-1.jpg?sig=abc...")
        # engagement always comes from the container, never the sub-item
        self.assertEqual(record["organic_like_count"], 648)
        self.assertEqual(record["organic_comment_count"], 19)
        self.assertIsNone(record["organic_view_count"])

    def test_carousel_uses_first_supported_item_video(self):
        record = norm("carousel_post_video_first.json")
        self.assertIsNotNone(record)
        self.assertEqual(record["post_type"], "video")
        self.assertEqual(record["media_url"], "https://scontent.cdninstagram.com/o1/v/t2/carousel-clip.mp4?sig=abc...")
        self.assertEqual(record["thumbnail_url"], "https://scontent.cdninstagram.com/v/carousel-clip-thumb.jpg?sig=abc...")
        # carousel sub-items never carry their own metrics - container's used
        self.assertEqual(record["organic_like_count"], 40)
        self.assertEqual(record["organic_comment_count"], 5)

    def test_zero_engagement_stays_zero_not_null(self):
        record = norm("zero_engagement_video.json")
        self.assertIsNotNone(record)
        self.assertEqual(record["organic_view_count"], 0)
        self.assertEqual(record["organic_like_count"], 0)
        self.assertEqual(record["organic_comment_count"], 0)

    def test_malformed_record_rejected(self):
        self.assertIsNone(norm("malformed.json"))

    def test_missing_post_id_rejected(self):
        self.assertIsNone(norm("missing_id.json"))

    def test_missing_media_rejected(self):
        self.assertIsNone(norm("missing_media.json"))

    def test_unsupported_media_type_rejected(self):
        self.assertIsNone(norm("unsupported_media_type.json"))

    def test_video_uses_first_valid_candidate_when_earlier_ones_are_bad(self):
        record = norm("video_post_later_candidate.json")
        self.assertIsNotNone(record)
        self.assertEqual(
            record["media_url"],
            "https://scontent.cdninstagram.com/o1/v/t2/later-candidate.mp4?sig=abc...",
        )
        self.assertEqual(
            record["thumbnail_url"],
            "https://scontent.cdninstagram.com/v/thumb-later.jpg?sig=abc...",
        )

    def test_boolean_taken_at_rejected_not_treated_as_timestamp(self):
        record = norm("boolean_timestamp.json")
        self.assertIsNotNone(record)  # post itself is still valid, just no date
        self.assertIsNone(record["published_at"])


class NormalizePostsListTests(unittest.TestCase):
    def test_deduplicates_keeping_first_valid(self):
        raw = [load("video_post.json"), load("duplicate_post.json")]
        posts = normalize_posts(raw, BRAND, HANDLE, PLATFORM)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["organic_like_count"], 3)  # first record's value, not the dup's 999

    def test_filters_and_preserves_order(self):
        raw = [
            load("image_post.json"),
            load("malformed.json"),
            load("missing_id.json"),
            load("unsupported_media_type.json"),
            load("missing_media.json"),
            load("video_post.json"),
            load("carousel_post.json"),
            load("duplicate_post.json"),
        ]
        posts = normalize_posts(raw, BRAND, HANDLE, PLATFORM)
        self.assertEqual(
            [p["post_id"] for p in posts],
            ["3900000000000000_11087474383", "3954222268720362185_11087474383", "3956409305604079263_11087474383"],
        )

    def test_empty_results(self):
        raw = load("empty_response.json")
        posts = normalize_posts(raw["items"], BRAND, HANDLE, PLATFORM)
        self.assertEqual(posts, [])


def _fake_fetch_returning(value):
    """Context manager: makes organic_fetcher.service.fetch_instagram_posts
    return `value` (or call `value()` if callable) instead of making a real
    request - lets us test service.py's shape-validation in isolation."""
    from organic_fetcher import service as organic_service

    class _Ctx:
        def __enter__(self_inner):
            self_inner.original = organic_service.fetch_instagram_posts
            organic_service.fetch_instagram_posts = (
                value if callable(value) else (lambda **_kwargs: value)
            )
            return organic_service

        def __exit__(self_inner, *exc_info):
            organic_service.fetch_instagram_posts = self_inner.original
            return False

    return _Ctx()


class ProviderErrorTests(unittest.TestCase):
    def test_missing_key_raises_without_making_a_request(self):
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_instagram_posts(api_key="", handle=HANDLE, timeout=5)
        self.assertIn("SCRAPECREATORS_API_KEY", str(ctx.exception))

    def test_error_messages_never_contain_api_key_source(self):
        source = (
            Path(__file__).resolve().parent.parent
            / "src" / "organic_fetcher" / "scrapecreators_client.py"
        ).read_text()
        for line in source.splitlines():
            if "raise ScrapeCreatorsError" in line or ("f\"" in line and "ScrapeCreators" in line):
                self.assertNotIn("api_key", line)

    def test_non_list_items_is_treated_as_provider_error(self):
        # service.py must reject this before normalizer.py ever sees it -
        # a malformed 'items' shape is a provider error, not zero results.
        raw = load("malformed_items_response.json")
        with _fake_fetch_returning(raw):
            with self.assertRaises(ScrapeCreatorsError):
                fetch_and_normalize()

    def test_top_level_list_response_is_a_provider_error(self):
        with _fake_fetch_returning(["not", "a", "dict"]):
            with self.assertRaises(ScrapeCreatorsError) as ctx:
                fetch_and_normalize()
        self.assertIn("JSON object", str(ctx.exception))

    def test_top_level_string_response_is_a_provider_error(self):
        with _fake_fetch_returning("not a dict either"):
            with self.assertRaises(ScrapeCreatorsError):
                fetch_and_normalize()

    def test_top_level_null_response_is_a_provider_error(self):
        with _fake_fetch_returning(None):
            with self.assertRaises(ScrapeCreatorsError):
                fetch_and_normalize()


SECRET_KEY = "sk_test_should_never_appear_anywhere"


class ProviderErrorBehaviorTests(unittest.TestCase):
    """Behavioral (mocked, no live requests/credits) checks on
    organic_fetcher's own HTTP client - mirrors ad_fetcher's equivalent
    tests. Supplements the source-scan test above with what the raised
    error messages actually look like at runtime."""

    @mock.patch("organic_fetcher.scrapecreators_client.time.sleep")
    @mock.patch("organic_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_auth_failure_message_and_no_key_leak(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_instagram_posts(api_key=SECRET_KEY, handle=HANDLE, timeout=5)
        self.assertIn("401", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))

    @mock.patch("organic_fetcher.scrapecreators_client.time.sleep")
    @mock.patch("organic_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_timeout_message_and_no_key_leak(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = TimeoutError()
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_instagram_posts(api_key=SECRET_KEY, handle=HANDLE, timeout=5)
        self.assertIn("timed out", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))

    @mock.patch("organic_fetcher.scrapecreators_client.time.sleep")
    @mock.patch("organic_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_network_error_message_and_no_key_leak(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = urllib.error.URLError("no route to host")
        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_instagram_posts(api_key=SECRET_KEY, handle=HANDLE, timeout=5)
        self.assertIn("no route to host", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))

    @mock.patch("organic_fetcher.scrapecreators_client.urllib.request.urlopen")
    def test_malformed_json_message_and_no_key_leak(self, mock_urlopen):
        response = mock.MagicMock()
        response.read.return_value = b"not json{"
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        mock_urlopen.return_value = response

        with self.assertRaises(ScrapeCreatorsError) as ctx:
            fetch_instagram_posts(api_key=SECRET_KEY, handle=HANDLE, timeout=5)
        self.assertIn("malformed JSON", str(ctx.exception))
        self.assertNotIn(SECRET_KEY, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
