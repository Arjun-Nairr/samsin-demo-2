"""Isolated Gemini image-generation call. Nothing else in this package
should know this is a specific REST API - generator.py works with plain
prompt text + reference image bytes in, image bytes out.

Plain stdlib urllib + json, matching every other provider client in this
repo (ScrapeCreators, Samsin) - no SDK dependency added for one endpoint.
"""
import base64
import json
import urllib.error
import urllib.request


class GeminiError(Exception):
    """Raised for any Gemini API failure. Message is safe to print -
    never includes the API key."""


def generate_image(
    prompt: str,
    reference_images: list,
    api_key: str,
    model: str,
    api_base: str,
    timeout: int,
) -> bytes:
    """`reference_images` is a list of raw image bytes (garment/model
    references). Returns the generated image's raw bytes. Raises
    GeminiError on any failure, including a response with no image."""
    if not api_key:
        raise GeminiError(
            "Missing GEMINI_API_KEY. Set it in .env or the environment before running."
        )

    parts = [{"text": prompt}]
    for image_bytes in reference_images:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode("ascii"),
            }
        })

    payload = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
    url = f"{api_base}/models/{model}:generateContent?key={api_key}"
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Deliberately not including the response body - it could echo
        # the request URL, which contains the API key as a query param.
        raise GeminiError(f"Gemini API returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise GeminiError(f"Gemini API request failed: {exc.reason}") from exc
    except TimeoutError:
        raise GeminiError(f"Gemini API request timed out after {timeout}s.")
    except json.JSONDecodeError as exc:
        raise GeminiError(f"Gemini API returned malformed JSON: {exc}") from exc

    try:
        response_parts = body["candidates"][0]["content"]["parts"]
        for part in response_parts:
            inline = part.get("inline_data") or part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiError("Gemini response was not in the expected shape.") from exc

    raise GeminiError("Gemini response did not contain an image.")
