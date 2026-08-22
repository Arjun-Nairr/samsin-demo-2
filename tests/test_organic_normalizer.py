"""Sequence B: deterministic cleanup against fixtures matching the real
(live-verified) ScrapeCreators Instagram Posts schema. stdlib unittest,
same pattern as tests/test_normalizer.py."""
import json
import sys
import unittest
from pathlib import Path

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
        from organic_fetcher import service as organic_service

        raw = load("malformed_items_response.json")

        class _FakeClientModule:
            @staticmethod
            def fetch_instagram_posts(**_kwargs):
                return raw

        original = organic_service.fetch_instagram_posts
        organic_service.fetch_instagram_posts = _FakeClientModule.fetch_instagram_posts
        try:
            with self.assertRaises(ScrapeCreatorsError):
                organic_service.fetch_and_normalize()
        finally:
            organic_service.fetch_instagram_posts = original


if __name__ == "__main__":
    unittest.main()
