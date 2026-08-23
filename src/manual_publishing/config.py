"""Sequence E, Part 4: this project's own publishing path, independent of
the old samsin-pricing-demo project - no shared code, no reused module.
Credentials and the Graph API version come entirely from environment
variables, per the brief.
"""
import os
from pathlib import Path

from ad_fetcher.config import load_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Real-publish cooldown state lives here - a tiny local file, not a
# database table, since it's one timestamp with no query needs.
COOLDOWN_STATE_PATH = PROJECT_ROOT / ".manual_publish_state.json"
COOLDOWN_SECONDS = 180

CONTAINER_POLL_MAX_ATTEMPTS = 10
CONTAINER_POLL_DELAY_SECONDS = 3

REQUEST_TIMEOUT_SECONDS = 30


def _env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key) or load_env().get(key) or default


def get_imgbb_api_key() -> str | None:
    return _env("IMGBB_API_KEY")


def get_ig_user_id() -> str | None:
    return _env("IG_USER_ID")


def get_ig_access_token() -> str | None:
    # Long-lived preferred, short-lived accepted - either env var name
    # works, whichever is set.
    return _env("IG_LONG_LIVED_TOKEN") or _env("IG_SHORT_LIVED_TOKEN")


def get_graph_api_version() -> str:
    return _env("IG_GRAPH_API_VERSION", "v21.0")
