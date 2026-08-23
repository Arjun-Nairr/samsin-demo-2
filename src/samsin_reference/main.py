"""CLI entrypoint. Same contract as every other CLI in this repo:
stdout=JSON only on success, stderr=diagnostics, non-zero exit on
failure. No credentials involved - this is a public website."""
import json
import sys

from .client import SamsinFetchError
from .service import fetch_tshirt_catalog


def main() -> int:
    try:
        output = fetch_tshirt_catalog()
    except SamsinFetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: unexpected failure ({exc.__class__.__name__}).", file=sys.stderr)
        return 1

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
