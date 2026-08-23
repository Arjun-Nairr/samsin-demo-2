"""CLI entrypoint. Prints ONLY the final JSON to stdout; diagnostics/errors
go to stderr; non-zero exit code on failure - keeps it pipeable into
automation later without building that automation now."""
import json
import sys

from .scrapecreators_client import ScrapeCreatorsError
from .service import fetch_and_normalize


def main() -> int:
    try:
        output = fetch_and_normalize()
    except ScrapeCreatorsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Never str(exc) here - an unexpected exception (unlike the
        # sanitized ScrapeCreatorsError above) could contain anything,
        # including a credential. Class name only.
        print(f"error: unexpected failure ({exc.__class__.__name__}).", file=sys.stderr)
        return 1

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
