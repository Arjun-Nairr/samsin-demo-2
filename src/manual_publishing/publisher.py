"""Sequence E, Part 4 orchestration: selected local image -> ImgBB public
URL -> Instagram media container -> wait for readiness -> publish.

Dry-run (default) exercises the whole pipeline except the final,
irreversible publish call - it uploads to ImgBB and creates+polls the
container (both reversible: nothing has posted yet), then stops. Only
`--publish` (main.py) calls the actual publish endpoint, and only after
the 180-second real-publish cooldown clears.
"""
import json
from datetime import datetime, timezone

from . import config
from .imgbb_client import upload_image
from .instagram_client import create_container, publish_container, wait_until_ready

GRAPH_API_BASE_TEMPLATE = "https://graph.instagram.com/{version}"


class CooldownError(Exception):
    """Raised when a real publish is attempted before the cooldown clears."""


def _read_cooldown_state() -> dict:
    if config.COOLDOWN_STATE_PATH.exists():
        return json.loads(config.COOLDOWN_STATE_PATH.read_text())
    return {}


def _write_cooldown_state(state: dict) -> None:
    config.COOLDOWN_STATE_PATH.write_text(json.dumps(state))


def check_cooldown() -> None:
    """Raises CooldownError if a real publish happened too recently.
    Only ever called before an actual (--publish) attempt - dry runs
    never touch this."""
    state = _read_cooldown_state()
    last = state.get("last_real_publish_at")
    if not last:
        return
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
    if elapsed < config.COOLDOWN_SECONDS:
        remaining = round(config.COOLDOWN_SECONDS - elapsed)
        raise CooldownError(
            f"A real publish happened {round(elapsed)}s ago - wait {remaining}s more "
            f"before the next real test publication ({config.COOLDOWN_SECONDS}s cooldown)."
        )


def _record_real_publish() -> None:
    _write_cooldown_state({"last_real_publish_at": datetime.now(timezone.utc).isoformat()})


def publish(image_path: str, caption: str, dry_run: bool = True) -> dict:
    """Returns a result dict. Never publishes for real unless dry_run is
    explicitly False - and even then, only after the cooldown clears."""
    if not dry_run:
        check_cooldown()

    imgbb_key = config.get_imgbb_api_key()
    ig_user_id = config.get_ig_user_id()
    access_token = config.get_ig_access_token()
    api_base = GRAPH_API_BASE_TEMPLATE.format(version=config.get_graph_api_version())

    image_url = upload_image(image_path, imgbb_key, config.REQUEST_TIMEOUT_SECONDS)

    creation_id = create_container(
        ig_user_id, access_token, image_url, caption, api_base, config.REQUEST_TIMEOUT_SECONDS
    )
    wait_until_ready(
        creation_id,
        access_token,
        api_base,
        config.REQUEST_TIMEOUT_SECONDS,
        config.CONTAINER_POLL_MAX_ATTEMPTS,
        config.CONTAINER_POLL_DELAY_SECONDS,
    )

    if dry_run:
        return {
            "dry_run": True,
            "image_url": image_url,
            "creation_id": creation_id,
            "published": False,
        }

    media_id = publish_container(ig_user_id, access_token, creation_id, api_base, config.REQUEST_TIMEOUT_SECONDS)
    _record_real_publish()
    return {
        "dry_run": False,
        "image_url": image_url,
        "creation_id": creation_id,
        "published": True,
        "media_id": media_id,
    }
