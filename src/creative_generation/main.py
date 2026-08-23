"""CLI for Sequence E, Part 3. Same contract as every other CLI in this
repo: stdout=JSON only on success, stderr=diagnostics, non-zero exit on
failure, GEMINI_API_KEY never printed.

Usage:
    python -m creative_generation.main generate \\
        --brief creative_brief.json --product product.json \\
        --garment <path_or_url> [--model-reference <path_or_url>]

    python -m creative_generation.main retry --run-dir <existing run dir>
"""
import argparse
import json
import sys

from .gemini_client import GeminiError
from .generator import generate_candidates, generate_one_more


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _load_json_file(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="creative_generation.main", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", add_help=False)
    generate_parser.add_argument("--brief", required=True)
    generate_parser.add_argument("--product", required=True)
    generate_parser.add_argument("--garment", required=True)
    generate_parser.add_argument("--model-reference", default=None)

    retry_parser = subparsers.add_parser("retry", add_help=False)
    retry_parser.add_argument("--run-dir", required=True)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return _fail("usage: generate --brief <file> --product <file> --garment <path_or_url> [--model-reference <path_or_url>] | retry --run-dir <dir>")

    try:
        if args.command == "generate":
            brief = _load_json_file(args.brief)
            product = _load_json_file(args.product)
            manifest = generate_candidates(
                creative_brief=brief,
                product=product,
                garment_reference=args.garment,
                model_reference=args.model_reference,
            )
        elif args.command == "retry":
            manifest = generate_one_more(args.run_dir)
        else:
            return _fail("usage: generate --brief <file> --product <file> --garment <path_or_url> [--model-reference <path_or_url>] | retry --run-dir <dir>")

    except GeminiError as exc:
        return _fail(str(exc))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _fail(f"invalid input ({exc.__class__.__name__}): {exc}")
    except Exception as exc:  # never str(exc) beyond the safe cases above
        return _fail(f"unexpected failure ({exc.__class__.__name__}).")

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
