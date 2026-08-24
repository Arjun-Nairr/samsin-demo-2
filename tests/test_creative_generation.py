"""Sequence E, Part 3: Gemini image-generation tool. No live network, no
live model call, no GEMINI_API_KEY needed - gemini_client.generate_image
is mocked throughout; real (Pillow-generated) PNG/JPEG bytes exercise the
deterministic dimension/format checks and the resize/crop step for real.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from creative_generation import config, generator, main as cg_main  # noqa: E402
from creative_generation.gemini_client import GeminiError, generate_image  # noqa: E402
from creative_generation.image_checks import ImageCheckError, validate_candidate  # noqa: E402

PRODUCT = {"title": "STAR T-SHIRT WHITE", "handle": "star-t-shirt-radiostar", "product_url": "https://shopsamsin.com/products/star-t-shirt-radiostar"}
BRIEF = {"tone": "bold streetwear", "notes": "clean background", "competitor_inspiration": "high-contrast lifestyle shots", "caption": "New drop just landed."}


def fake_png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def fake_jpeg(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buf, format="JPEG")
    return buf.getvalue()


class BuildPromptTests(unittest.TestCase):
    def test_prompt_includes_product_identity_and_safety_constraints(self):
        prompt = generator.build_prompt(BRIEF, PRODUCT)
        self.assertIn("STAR T-SHIRT WHITE", prompt)
        self.assertIn("bold streetwear", prompt)
        self.assertIn("clean background", prompt)
        self.assertIn("high-contrast lifestyle shots", prompt)
        self.assertIn("never copy any competitor logo", prompt)
        self.assertIn("Do not include any price", prompt)
        self.assertIn(f"{config.CANDIDATE_WIDTH}x{config.CANDIDATE_HEIGHT}", prompt)
        self.assertNotIn("caption", prompt.lower())  # caption is for Part 4, not the image

    def test_prompt_never_invents_pricing_or_discount_text(self):
        prompt = generator.build_prompt({}, PRODUCT)
        self.assertNotIn("%", prompt)
        self.assertNotIn("$", prompt)

    def test_model_reference_adds_identity_preservation_priority(self):
        prompt = generator.build_prompt(BRIEF, PRODUCT, model_reference="https://example.com/model.png")
        self.assertIn("HIGHEST PRIORITY", prompt)
        self.assertIn("model's identity", prompt)
        self.assertIn("preservation wins", prompt)

    def test_no_model_reference_omits_identity_preservation_language(self):
        prompt = generator.build_prompt(BRIEF, PRODUCT, model_reference=None)
        self.assertNotIn("HIGHEST PRIORITY", prompt)
        self.assertNotIn("model's identity", prompt)


class ImageChecksTests(unittest.TestCase):
    def test_valid_png_matching_dimensions(self):
        fmt = validate_candidate(fake_png(1080, 1350), 1080, 1350)
        self.assertEqual(fmt, "png")

    def test_valid_jpeg_matching_dimensions(self):
        fmt = validate_candidate(fake_jpeg(1080, 1350), 1080, 1350)
        self.assertEqual(fmt, "jpeg")

    def test_wrong_dimensions_rejected(self):
        with self.assertRaises(ImageCheckError):
            validate_candidate(fake_png(500, 500), 1080, 1350)

    def test_unreadable_data_rejected(self):
        with self.assertRaises(ImageCheckError):
            validate_candidate(b"not an image", 1080, 1350)


class GeminiClientTests(unittest.TestCase):
    def test_missing_key_raises_without_a_request(self):
        with self.assertRaises(GeminiError) as ctx:
            generate_image("prompt", [], api_key="", model="m", api_base="https://x", timeout=5)
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    @mock.patch("creative_generation.gemini_client.urllib.request.urlopen")
    def test_successful_generation_returns_image_bytes(self, mock_urlopen):
        import base64
        png = fake_png(1080, 1350)
        body = {"candidates": [{"content": {"parts": [{"inline_data": {"data": base64.b64encode(png).decode()}}]}}]}
        response = mock.MagicMock()
        response.read.return_value = json.dumps(body).encode()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        mock_urlopen.return_value = response

        result = generate_image("prompt", [b"ref"], api_key="k", model="m", api_base="https://x", timeout=5)
        self.assertEqual(result, png)

    @mock.patch("creative_generation.gemini_client.urllib.request.urlopen")
    def test_response_without_image_raises(self, mock_urlopen):
        response = mock.MagicMock()
        response.read.return_value = json.dumps({"candidates": [{"content": {"parts": [{"text": "no image"}]}}]}).encode()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        mock_urlopen.return_value = response

        with self.assertRaises(GeminiError):
            generate_image("prompt", [], api_key="k", model="m", api_base="https://x", timeout=5)

    @mock.patch("creative_generation.gemini_client.urllib.request.urlopen")
    def test_http_error_and_no_key_leak(self, mock_urlopen):
        import urllib.error
        secret = "sk_test_gemini_key"
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        with self.assertRaises(GeminiError) as ctx:
            generate_image("prompt", [], api_key=secret, model="m", api_base="https://x", timeout=5)
        self.assertNotIn(secret, str(ctx.exception))
        self.assertIn("403", str(ctx.exception))


class GenerateCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output_dir_patch = mock.patch.object(config, "OUTPUT_DIR", Path(self.tmp.name))
        self.output_dir_patch.start()
        self.addCleanup(self.output_dir_patch.stop)

        self.garment_path = Path(self.tmp.name) / "garment.jpg"
        self.garment_path.write_bytes(b"fake-garment-bytes")
        self.model_path = Path(self.tmp.name) / "model.jpg"
        self.model_path.write_bytes(b"fake-model-bytes")

    def _mock_generate_image(self, *_args, **_kwargs):
        return fake_png(config.CANDIDATE_WIDTH, config.CANDIDATE_HEIGHT)

    def test_generates_expected_number_of_candidates_with_manifest(self):
        with mock.patch("creative_generation.generator.generate_image", side_effect=self._mock_generate_image):
            with mock.patch.object(config, "get_gemini_api_key", return_value="k"):
                manifest = generator.generate_candidates(BRIEF, PRODUCT, str(self.garment_path), None)

        self.assertEqual(len(manifest["candidates"]), config.NUM_CANDIDATES)
        for candidate in manifest["candidates"]:
            self.assertTrue(candidate["passed_checks"])
            self.assertTrue(Path(candidate["output_path"]).exists())
        self.assertEqual(manifest["product"]["handle"], "star-t-shirt-radiostar")
        self.assertIn("prompt", manifest)
        manifest_file = list(Path(self.tmp.name).glob("*/manifest.json"))
        self.assertEqual(len(manifest_file), 1)

    def test_model_reference_is_recorded_and_flows_into_the_prompt(self):
        with mock.patch("creative_generation.generator.generate_image", side_effect=self._mock_generate_image):
            with mock.patch.object(config, "get_gemini_api_key", return_value="k"):
                manifest = generator.generate_candidates(
                    BRIEF, PRODUCT, str(self.garment_path), str(self.model_path), num_candidates=1
                )

        self.assertEqual(manifest["model_reference"], str(self.model_path))
        self.assertIn("HIGHEST PRIORITY", manifest["prompt"])

    def test_resize_normalizes_a_differently_sized_model_output(self):
        # Confirmed live: Gemini doesn't reliably honor the exact requested
        # pixel size (returned 1024x1024 for a requested 1080x1350) - the
        # deterministic resize/crop step must still land on the exact
        # target dimensions regardless of the model's native output size.
        def off_size_generate(*_args, **_kwargs):
            return fake_png(1024, 1024)

        with mock.patch("creative_generation.generator.generate_image", side_effect=off_size_generate):
            with mock.patch.object(config, "get_gemini_api_key", return_value="k"):
                manifest = generator.generate_candidates(BRIEF, PRODUCT, str(self.garment_path), None, num_candidates=1)

        candidate = manifest["candidates"][0]
        self.assertTrue(candidate["passed_checks"])
        with Image.open(candidate["output_path"]) as saved:
            self.assertEqual(saved.size, (config.CANDIDATE_WIDTH, config.CANDIDATE_HEIGHT))

    def test_unreadable_model_output_is_recorded_not_silently_dropped(self):
        def bad_generate(*_args, **_kwargs):
            return b"not an image at all"

        with mock.patch("creative_generation.generator.generate_image", side_effect=bad_generate):
            with mock.patch.object(config, "get_gemini_api_key", return_value="k"):
                manifest = generator.generate_candidates(BRIEF, PRODUCT, str(self.garment_path), None, num_candidates=1)

        candidate = manifest["candidates"][0]
        self.assertFalse(candidate["passed_checks"])
        self.assertIsNotNone(candidate["check_error"])
        self.assertTrue(Path(candidate["output_path"]).exists())  # still saved for inspection

    def test_retry_appends_one_candidate_reusing_the_same_prompt(self):
        with mock.patch("creative_generation.generator.generate_image", side_effect=self._mock_generate_image):
            with mock.patch.object(config, "get_gemini_api_key", return_value="k"):
                manifest = generator.generate_candidates(BRIEF, PRODUCT, str(self.garment_path), None, num_candidates=1)

        run_dir = str(Path(manifest["candidates"][0]["output_path"]).parent)
        with mock.patch("creative_generation.generator.generate_image", side_effect=self._mock_generate_image):
            updated = generator.generate_one_more(run_dir)

        self.assertEqual(len(updated["candidates"]), 2)
        self.assertTrue(updated["candidates"][1]["retry"])
        self.assertEqual(updated["prompt"], manifest["prompt"])  # same prompt, real retry


class CliTests(unittest.TestCase):
    def test_unexpected_exception_never_leaks_a_secret(self):
        secret = "sk_test_totally_secret"
        with mock.patch("creative_generation.main.generate_candidates", side_effect=Exception(f"boom {secret}")):
            stderr = io.StringIO()
            with tempfile.TemporaryDirectory() as tmp:
                brief_path = Path(tmp) / "brief.json"
                product_path = Path(tmp) / "product.json"
                brief_path.write_text("{}")
                product_path.write_text("{}")
                with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                    code = cg_main.main([
                        "generate", "--brief", str(brief_path), "--product", str(product_path),
                        "--garment", "https://example.com/x.jpg",
                    ])
        self.assertEqual(code, 1)
        self.assertNotIn(secret, stderr.getvalue())
        self.assertIn("Exception", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
