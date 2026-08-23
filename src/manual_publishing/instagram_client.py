"""Isolated Instagram Graph API calls: create a media container, poll its
status, publish it. Fresh implementation for this project - no import
from or dependency on the old samsin-pricing-demo project.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class InstagramError(Exception):
    """Raised for any Instagram Graph API failure. Message is safe to
    print - never includes the access token."""


def _request(url: str, timeout: int, method: str = "GET") -> dict:
    request = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Deliberately not echoing the response body or URL - the access
        # token is a query parameter on every one of these URLs.
        raise InstagramError(f"Instagram Graph API returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise InstagramError(f"Instagram Graph API request failed: {exc.reason}") from exc
    except TimeoutError:
        raise InstagramError(f"Instagram Graph API request timed out after {timeout}s.")
    except json.JSONDecodeError as exc:
        raise InstagramError(f"Instagram Graph API returned malformed JSON: {exc}") from exc


def create_container(
    ig_user_id: str, access_token: str, image_url: str, caption: str, api_base: str, timeout: int
) -> str:
    """Returns the new container's creation_id."""
    url = (
        f"{api_base}/{ig_user_id}/media"
        f"?image_url={urllib.parse.quote(image_url, safe='')}"
        f"&caption={urllib.parse.quote(caption, safe='')}"
        f"&access_token={access_token}"
    )
    body = _request(url, timeout, method="POST")
    if "id" not in body:
        raise InstagramError("Container creation did not return an id.")
    return body["id"]


def get_container_status(container_id: str, access_token: str, api_base: str, timeout: int) -> str:
    url = f"{api_base}/{container_id}?fields=status_code&access_token={access_token}"
    body = _request(url, timeout)
    status = body.get("status_code")
    if not status:
        raise InstagramError("Container status response did not contain a status_code.")
    return status


def wait_until_ready(
    container_id: str, access_token: str, api_base: str, timeout: int, max_attempts: int, delay_seconds: int
) -> None:
    """Polls with bounded retries. Raises InstagramError if the container
    errors out or never reaches FINISHED within max_attempts."""
    for attempt in range(1, max_attempts + 1):
        status = get_container_status(container_id, access_token, api_base, timeout)
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise InstagramError("Instagram reported the container failed processing (status_code=ERROR).")
        if attempt < max_attempts:
            time.sleep(delay_seconds)
    raise InstagramError(f"Container did not become ready after {max_attempts} attempts.")


def publish_container(ig_user_id: str, access_token: str, creation_id: str, api_base: str, timeout: int) -> str:
    """Returns the published media's id."""
    url = f"{api_base}/{ig_user_id}/media_publish?creation_id={creation_id}&access_token={access_token}"
    body = _request(url, timeout, method="POST")
    if "id" not in body:
        raise InstagramError("Publish did not return a media id.")
    return body["id"]
