"""CLI for Sequence E, Part 4. Same contract as every other CLI in this
repo: stdout=JSON only on success, stderr=diagnostics, non-zero exit on
failure. Never prints IMGBB_API_KEY, IG_LONG_LIVED_TOKEN/IG_SHORT_LIVED_TOKEN,
or DATABASE_URL.

Usage:
    python -m manual_publishing.main --image <path> --brief <creative_brief.json>   (dry run, default)
    python -m manual_publishing.main --image <path> --brief <creative_brief.json> --publish   (real)
"""
import argparse
import json
import sys

from .imgbb_client import ImgbbError
from .instagram_client import InstagramError
from .publisher import CooldownError, publish


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="manual_publishing.main", add_help=False)
    parser.add_argument("--image", required=True)
    parser.add_argument("--brief", required=True, help="creative_brief.json - its 'caption' field is used verbatim")
    parser.add_argument("--publish", action="store_true", help="actually publish (default is dry-run)")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return _fail("usage: --image <path> --brief <creative_brief.json> [--publish]")

    try:
        with open(args.brief, encoding="utf-8") as f:
            brief = json.load(f)
        caption = brief.get("caption", "")
        if not isinstance(caption, str):
            return _fail("creative brief's 'caption' field must be a string.")

        result = publish(args.image, caption, dry_run=not args.publish)

    except CooldownError as exc:
        return _fail(str(exc))
    except (ImgbbError, InstagramError) as exc:
        return _fail(str(exc))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _fail(f"invalid input ({exc.__class__.__name__}): {exc}")
    except Exception as exc:  # never str(exc) beyond the safe cases above
        return _fail(f"unexpected failure ({exc.__class__.__name__}).")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
