"""Sequence E, Part 4: manual publishing (ImgBB + Instagram). No live
network anywhere - urllib.request.urlopen is mocked throughout. The
cooldown state file is redirected to a temp path per test.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from manual_publishing import config, main as mp_main  # noqa: E402
from manual_publishing.imgbb_client import ImgbbError, upload_image  # noqa: E402
from manual_publishing.instagram_client import (  # noqa: E402
    InstagramError,
    create_container,
    get_container_status,
    wait_until_ready,
)
from manual_publishing.publisher import CooldownError, publish  # noqa: E402


def _fake_response(payload: dict):
    response = mock.MagicMock()
    response.read.return_value = json.dumps(payload).encode()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


class ImgbbClientTests(unittest.TestCase):
    def test_missing_key_raises_without_a_request(self):
        with self.assertRaises(ImgbbError) as ctx:
            upload_image("x.jpg", api_key="", timeout=5)
        self.assertIn("IMGBB_API_KEY", str(ctx.exception))

    @mock.patch("manual_publishing.imgbb_client.urllib.request.urlopen")
    def test_successful_upload_returns_url(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"success": True, "data": {"url": "https://i.ibb.co/x.jpg"}})
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake-image-bytes")
            path = f.name
        url = upload_image(path, api_key="k", timeout=5)
        self.assertEqual(url, "https://i.ibb.co/x.jpg")

    @mock.patch("manual_publishing.imgbb_client.urllib.request.urlopen")
    def test_unsuccessful_response_raises(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"success": False})
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"x")
            path = f.name
        with self.assertRaises(ImgbbError):
            upload_image(path, api_key="k", timeout=5)


class InstagramClientTests(unittest.TestCase):
    @mock.patch("manual_publishing.instagram_client.urllib.request.urlopen")
    def test_create_container_returns_id(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"id": "container123"})
        result = create_container("uid", "token", "https://x/img.jpg", "caption", "https://graph.instagram.com/v21.0", 5)
        self.assertEqual(result, "container123")

    @mock.patch("manual_publishing.instagram_client.time.sleep")
    @mock.patch("manual_publishing.instagram_client.urllib.request.urlopen")
    def test_wait_until_ready_polls_then_succeeds(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            _fake_response({"status_code": "IN_PROGRESS"}),
            _fake_response({"status_code": "IN_PROGRESS"}),
            _fake_response({"status_code": "FINISHED"}),
        ]
        wait_until_ready("c1", "token", "https://graph.instagram.com/v21.0", 5, max_attempts=5, delay_seconds=1)
        self.assertEqual(mock_sleep.call_count, 2)

    @mock.patch("manual_publishing.instagram_client.time.sleep")
    @mock.patch("manual_publishing.instagram_client.urllib.request.urlopen")
    def test_wait_until_ready_bounded_gives_up(self, mock_urlopen, mock_sleep):
        mock_urlopen.return_value = _fake_response({"status_code": "IN_PROGRESS"})
        with self.assertRaises(InstagramError):
            wait_until_ready("c1", "token", "https://graph.instagram.com/v21.0", 5, max_attempts=3, delay_seconds=1)
        self.assertEqual(mock_urlopen.call_count, 3)  # never polls indefinitely

    @mock.patch("manual_publishing.instagram_client.urllib.request.urlopen")
    def test_error_status_raises_immediately(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"status_code": "ERROR"})
        with self.assertRaises(InstagramError):
            wait_until_ready("c1", "token", "https://graph.instagram.com/v21.0", 5, max_attempts=5, delay_seconds=1)

    @mock.patch("manual_publishing.instagram_client.urllib.request.urlopen")
    def test_http_error_never_leaks_the_token(self, mock_urlopen):
        import urllib.error
        secret = "sk_test_ig_token"
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
        with self.assertRaises(InstagramError) as ctx:
            get_container_status("c1", secret, "https://graph.instagram.com/v21.0", 5)
        self.assertNotIn(secret, str(ctx.exception))


class PublisherCooldownTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state_path = Path(self.tmp.name) / "state.json"
        self.patch = mock.patch.object(config, "COOLDOWN_STATE_PATH", self.state_path)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def _fully_mocked_publish(self, dry_run):
        with mock.patch("manual_publishing.publisher.upload_image", return_value="https://i.ibb.co/x.jpg"):
            with mock.patch("manual_publishing.publisher.create_container", return_value="c1"):
                with mock.patch("manual_publishing.publisher.wait_until_ready"):
                    with mock.patch("manual_publishing.publisher.publish_container", return_value="media123"):
                        return publish("img.jpg", "caption text", dry_run=dry_run)

    def test_dry_run_never_calls_publish_container(self):
        with mock.patch("manual_publishing.publisher.upload_image", return_value="https://i.ibb.co/x.jpg"):
            with mock.patch("manual_publishing.publisher.create_container", return_value="c1") as mock_create:
                with mock.patch("manual_publishing.publisher.wait_until_ready") as mock_wait:
                    with mock.patch("manual_publishing.publisher.publish_container") as mock_publish:
                        result = publish("img.jpg", "caption", dry_run=True)
        mock_create.assert_called_once()
        mock_wait.assert_called_once()
        mock_publish.assert_not_called()
        self.assertFalse(result["published"])
        self.assertTrue(result["dry_run"])

    def test_real_publish_calls_every_step_and_records_cooldown(self):
        result = self._fully_mocked_publish(dry_run=False)
        self.assertTrue(result["published"])
        self.assertEqual(result["media_id"], "media123")
        self.assertTrue(self.state_path.exists())

    def test_second_real_publish_within_cooldown_is_blocked(self):
        self._fully_mocked_publish(dry_run=False)
        with self.assertRaises(CooldownError):
            self._fully_mocked_publish(dry_run=False)

    def test_real_publish_allowed_after_cooldown_elapses(self):
        old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=config.COOLDOWN_SECONDS + 5)).isoformat()
        self.state_path.write_text(json.dumps({"last_real_publish_at": old_timestamp}))
        result = self._fully_mocked_publish(dry_run=False)
        self.assertTrue(result["published"])

    def test_dry_run_never_checks_or_touches_cooldown(self):
        self._fully_mocked_publish(dry_run=False)  # sets cooldown
        # A dry run right after a real publish must still work - it never
        # calls check_cooldown at all.
        with mock.patch("manual_publishing.publisher.upload_image", return_value="https://i.ibb.co/x.jpg"):
            with mock.patch("manual_publishing.publisher.create_container", return_value="c2"):
                with mock.patch("manual_publishing.publisher.wait_until_ready"):
                    result = publish("img.jpg", "caption", dry_run=True)
        self.assertFalse(result["published"])


class CliTests(unittest.TestCase):
    def test_unexpected_exception_never_leaks_a_secret(self):
        secret = "sk_test_totally_secret_token"
        with mock.patch("manual_publishing.main.publish", side_effect=Exception(f"boom {secret}")):
            with tempfile.TemporaryDirectory() as tmp:
                brief_path = Path(tmp) / "brief.json"
                brief_path.write_text(json.dumps({"caption": "hello"}))
                image_path = Path(tmp) / "img.jpg"
                image_path.write_bytes(b"x")
                stderr = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                    code = mp_main.main(["--image", str(image_path), "--brief", str(brief_path)])
        self.assertEqual(code, 1)
        self.assertNotIn(secret, stderr.getvalue())

    def test_dry_run_is_the_default_without_publish_flag(self):
        with mock.patch("manual_publishing.main.publish", return_value={"dry_run": True, "published": False}) as mock_publish:
            with tempfile.TemporaryDirectory() as tmp:
                brief_path = Path(tmp) / "brief.json"
                brief_path.write_text(json.dumps({"caption": "hello"}))
                image_path = Path(tmp) / "img.jpg"
                image_path.write_bytes(b"x")
                with redirect_stdout(io.StringIO()):
                    mp_main.main(["--image", str(image_path), "--brief", str(brief_path)])
        self.assertTrue(mock_publish.call_args.kwargs["dry_run"])

    def test_publish_flag_requests_a_real_publish(self):
        with mock.patch("manual_publishing.main.publish", return_value={"dry_run": False, "published": True, "media_id": "m1"}) as mock_publish:
            with tempfile.TemporaryDirectory() as tmp:
                brief_path = Path(tmp) / "brief.json"
                brief_path.write_text(json.dumps({"caption": "hello"}))
                image_path = Path(tmp) / "img.jpg"
                image_path.write_bytes(b"x")
                with redirect_stdout(io.StringIO()):
                    mp_main.main(["--image", str(image_path), "--brief", str(brief_path), "--publish"])
        self.assertFalse(mock_publish.call_args.kwargs["dry_run"])


if __name__ == "__main__":
    unittest.main()
