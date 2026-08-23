"""Deterministic checks only - valid image, correct dimensions, expected
format. No visual/semantic QA, no autonomous critic (a human selects the
candidate; OpenClaw does semantic QA later).

Uses Pillow to read/verify the image - not hand-rolled header parsing.
Pillow is a genuine dependency of this package already (generator.py needs
it for the deterministic resize/crop step; see there), so reusing it here
for two integers and a format string is simpler and more robust than a
second, bespoke implementation.
"""
import io

from PIL import Image, UnidentifiedImageError


class ImageCheckError(Exception):
    """Raised when a generated candidate fails a deterministic check."""


def validate_candidate(data: bytes, expected_width: int, expected_height: int) -> str:
    """Returns the detected format (lowercase, e.g. "png") if the image is
    readable and exactly the expected dimensions. Raises ImageCheckError
    otherwise - never silently accepts a wrong-shaped or unreadable file.
    """
    if not isinstance(data, bytes) or not data:
        raise ImageCheckError("Output is not a readable file.")

    try:
        image = Image.open(io.BytesIO(data))
        image_format = image.format
        width, height = image.size
        image.verify()  # raises if the pixel data itself is corrupt
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageCheckError(f"Output is not a readable image ({exc}).") from exc

    if not image_format:
        raise ImageCheckError("Output's image format could not be determined.")
    if (width, height) != (expected_width, expected_height):
        raise ImageCheckError(
            f"Expected {expected_width}x{expected_height}, got {width}x{height}."
        )
    return image_format.lower()
