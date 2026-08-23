"""Isolated ImgBB upload call. Nothing else in this package should know
this is ImgBB specifically - publisher.py just wants a local image path
in, a public URL out.
"""
import base64
import json
import urllib.error
import urllib.parse
import urllib.request

UPLOAD_URL = "https://api.imgbb.com/1/upload"
DEFAULT_EXPIRY_SECONDS = 86_400  # 1 day - Instagram re-hosts its own copy at publish time


class ImgbbError(Exception):
    """Raised for any ImgBB failure. Message is safe to print - never
    includes the API key."""


def upload_image(image_path: str, api_key: str, timeout: int, expiration: int = DEFAULT_EXPIRY_SECONDS) -> str:
    if not api_key:
        raise ImgbbError("Missing IMGBB_API_KEY. Set it in .env or the environment before running.")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    payload = urllib.parse.urlencode({
        "key": api_key,
        "image": base64.b64encode(image_bytes).decode("ascii"),
        "expiration": expiration,
    }).encode()

    request = urllib.request.Request(UPLOAD_URL, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ImgbbError(f"ImgBB upload returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ImgbbError(f"ImgBB upload failed: {exc.reason}") from exc
    except TimeoutError:
        raise ImgbbError(f"ImgBB upload timed out after {timeout}s.")
    except json.JSONDecodeError as exc:
        raise ImgbbError(f"ImgBB returned malformed JSON: {exc}") from exc

    if not body.get("success"):
        raise ImgbbError("ImgBB upload did not report success.")
    try:
        return body["data"]["url"]
    except (KeyError, TypeError) as exc:
        raise ImgbbError("ImgBB response did not contain a URL.") from exc
