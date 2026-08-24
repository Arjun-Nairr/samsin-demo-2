"""CLI for the Sequence F run lock. Same contract as every other CLI in
this repo: stdout=JSON only on success, stderr=diagnostics, non-zero exit
on failure.

Usage:
    python -m pipeline_run.main acquire --run-id <id> --mode dry-run|publish
    python -m pipeline_run.main release
"""
import argparse
import json
import sys

from .lock import LockHeldError, acquire, release


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="pipeline_run.main", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    acquire_parser = subparsers.add_parser("acquire", add_help=False)
    acquire_parser.add_argument("--run-id", required=True)
    acquire_parser.add_argument("--mode", required=True, choices=["dry-run", "publish"])

    subparsers.add_parser("release", add_help=False)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return _fail("usage: acquire --run-id <id> --mode dry-run|publish | release")

    try:
        if args.command == "acquire":
            result = acquire(args.run_id, args.mode)
        elif args.command == "release":
            release()
            result = {"released": True}
        else:
            return _fail("usage: acquire --run-id <id> --mode dry-run|publish | release")
    except LockHeldError as exc:
        return _fail(str(exc))
    except Exception as exc:  # never str(exc) beyond the safe case above
        return _fail(f"unexpected failure ({exc.__class__.__name__}).")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
