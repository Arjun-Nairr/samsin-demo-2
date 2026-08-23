"""CLI entrypoint. Same contract as ad_fetcher/organic_fetcher: stdout=JSON
only on success, stderr=diagnostics, non-zero exit on failure, never prints
SCRAPECREATORS_API_KEY or DATABASE_URL."""
import json
import sys

from ad_fetcher.scrapecreators_client import ScrapeCreatorsError

from .db import PersistenceError
from .service import refresh_competitive_memory


def main() -> int:
    try:
        output = refresh_competitive_memory()
    except (ScrapeCreatorsError, PersistenceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Never str(exc) here - an unexpected exception (unlike the
        # sanitized ScrapeCreatorsError/PersistenceError above) could
        # contain anything, including DATABASE_URL or the API key.
        print(f"error: unexpected failure ({exc.__class__.__name__}).", file=sys.stderr)
        return 1

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
