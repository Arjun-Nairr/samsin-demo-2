"""Sequence E, Part 3: everything configured through environment
variables, per the brief. Reuses ad_fetcher's .env parser (provider-
agnostic - just reads KEY=VALUE lines) rather than duplicating it.
"""
import os
from pathlib import Path

from ad_fetcher.config import load_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "generated_creatives"

CANDIDATE_WIDTH = 1080
CANDIDATE_HEIGHT = 1350
NUM_CANDIDATES = 2

REQUEST_TIMEOUT_SECONDS = 60


def _env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key) or load_env().get(key) or default


def get_gemini_api_key() -> str | None:
    return _env("GEMINI_API_KEY")


def get_gemini_model() -> str:
    # Env-overridable on purpose: Gemini's image-generation model name is
    # not verified against a live key in this environment - if it's wrong,
    # this can be corrected without a code change.
    return _env("GEMINI_MODEL", "gemini-2.5-flash-image")


def get_gemini_api_base() -> str:
    return _env("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
