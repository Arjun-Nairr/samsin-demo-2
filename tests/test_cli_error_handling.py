"""Behavioral tests: when a CLI's underlying call raises an *unexpected*
exception (not the sanitized ScrapeCreatorsError/PersistenceError types),
the generic fallback in main() must never print that exception's raw text
- it could contain a credential. Applies identically to all three CLIs.

No live network, no live database - each CLI's own top-level function is
mocked to raise the fake-secret exception directly.
"""
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

FAKE_API_KEY = "sk_live_totally_secret_scrapecreators_key"
FAKE_DSN = "postgresql://user:sk_super_secret_password@example.com/db"


class UnexpectedExceptionNeverLeaksSecretsTests(unittest.TestCase):
    def _run_main_with(self, target, exc, main_module):
        with mock.patch(target, side_effect=exc):
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                exit_code = main_module.main()
        return exit_code, stderr.getvalue()

    def test_ad_fetcher_main_never_leaks_a_secret_from_an_unexpected_exception(self):
        from ad_fetcher import main as ad_main

        exit_code, stderr = self._run_main_with(
            "ad_fetcher.main.fetch_and_normalize",
            Exception(f"boom, key was {FAKE_API_KEY}"),
            ad_main,
        )
        self.assertEqual(exit_code, 1)
        self.assertNotIn(FAKE_API_KEY, stderr)
        self.assertIn("Exception", stderr)
        self.assertIn("unexpected failure", stderr)

    def test_organic_fetcher_main_never_leaks_a_secret_from_an_unexpected_exception(self):
        from organic_fetcher import main as organic_main

        exit_code, stderr = self._run_main_with(
            "organic_fetcher.main.fetch_and_normalize",
            Exception(f"boom, key was {FAKE_API_KEY}"),
            organic_main,
        )
        self.assertEqual(exit_code, 1)
        self.assertNotIn(FAKE_API_KEY, stderr)
        self.assertIn("Exception", stderr)

    def test_competitive_memory_main_never_leaks_the_api_key(self):
        from competitive_memory import main as cm_main

        exit_code, stderr = self._run_main_with(
            "competitive_memory.main.refresh_competitive_memory",
            Exception(f"boom, key was {FAKE_API_KEY}"),
            cm_main,
        )
        self.assertEqual(exit_code, 1)
        self.assertNotIn(FAKE_API_KEY, stderr)

    def test_competitive_memory_main_never_leaks_the_dsn(self):
        from competitive_memory import main as cm_main

        exit_code, stderr = self._run_main_with(
            "competitive_memory.main.refresh_competitive_memory",
            RuntimeError(f"unexpected: dsn was {FAKE_DSN}"),
            cm_main,
        )
        self.assertEqual(exit_code, 1)
        self.assertNotIn(FAKE_DSN, stderr)
        self.assertNotIn("sk_super_secret_password", stderr)
        self.assertIn("RuntimeError", stderr)

    def test_expected_sanitized_errors_still_print_normally(self):
        # The fix must not touch the already-sanitized ScrapeCreatorsError/
        # PersistenceError path - those messages are safe and should still
        # appear verbatim for debuggability.
        from ad_fetcher import main as ad_main
        from ad_fetcher.scrapecreators_client import ScrapeCreatorsError

        exit_code, stderr = self._run_main_with(
            "ad_fetcher.main.fetch_and_normalize",
            ScrapeCreatorsError("ScrapeCreators authentication failed (HTTP 401)."),
            ad_main,
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("ScrapeCreators authentication failed (HTTP 401).", stderr)


if __name__ == "__main__":
    unittest.main()
