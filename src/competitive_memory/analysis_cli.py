"""CLI for the Sequence D analysis-persistence boundary: list pending
work, save a completed analysis, or mark one failed.

The analysis JSON is read from stdin (not argv) so a large payload and
shell-escaping are never fragile - see `save`. Same contract as every
other CLI here: stdout carries only the final JSON on success, diagnostics
go to stderr, non-zero exit on failure, no credential ever printed.

Usage:
    python -m competitive_memory.analysis_cli pending [limit]
    python -m competitive_memory.analysis_cli save <ad_id>   < result.json
    python -m competitive_memory.analysis_cli fail <ad_id> [error message]
        (omit the message to read it from stdin instead)
"""
import json
import sys

from .analysis import list_pending_analysis, mark_failed, save_analysis
from .db import PersistenceError


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return _fail("usage: analysis_cli <pending|save|fail> [args...]")

    command, rest = argv[0], argv[1:]

    try:
        if command == "pending":
            limit = int(rest[0]) if rest else None
            output = {"pending": list_pending_analysis(limit)}

        elif command == "save":
            if not rest:
                return _fail("usage: analysis_cli save <ad_id>  (reads analysis JSON from stdin)")
            ad_id = rest[0]
            try:
                result = json.load(sys.stdin)
            except json.JSONDecodeError as exc:
                return _fail(f"stdin was not valid JSON ({exc}).")
            save_analysis(ad_id, result)
            output = {"ad_id": ad_id, "status": "complete"}

        elif command == "fail":
            if not rest:
                return _fail("usage: analysis_cli fail <ad_id> [error message]  (or reads it from stdin)")
            ad_id = rest[0]
            error_message = " ".join(rest[1:]) if len(rest) > 1 else sys.stdin.read().strip()
            mark_failed(ad_id, error_message)
            output = {"ad_id": ad_id, "status": "failed"}

        else:
            return _fail(f"unknown command: {command!r} (expected pending, save, or fail)")

    except PersistenceError as exc:
        return _fail(str(exc))
    except Exception as exc:  # never str(exc) - see ad_fetcher/organic_fetcher/main.py
        return _fail(f"unexpected failure ({exc.__class__.__name__}).")

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
