"""CLI for hold-region review artifact inspection."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from .review_artifacts import discover_review_run, inspect_run


def main(argv: Sequence[str] | None = None) -> int:
    """Run one review command and return a process-style exit code."""
    try:
        arguments = _parser().parse_args(argv)
        payload = _run(arguments)
    except SystemExit as error:
        return int(error.code or 0)
    except (OSError, ValueError) as error:
        print(f"error: {_first_line(error)}", file=sys.stderr)
        return 3
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hangboard-review",
        description="Inspect hold-region review artifacts for one onboarding run.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    inspect = subcommands.add_parser(
        "inspect", help="summarize the current review artifact state"
    )
    inspect.add_argument("--run", type=Path, required=True, help="review run directory")
    inspect.add_argument(
        "--json",
        action="store_true",
        help="print compact JSON output (default behavior)",
    )
    return parser


def _run(arguments: argparse.Namespace) -> dict[str, object]:
    if arguments.command != "inspect":
        raise ValueError(f"unsupported command: {arguments.command}")
    run = discover_review_run(arguments.run)
    return inspect_run(run)


def _first_line(error: BaseException) -> str:
    message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
    return message


if __name__ == "__main__":
    raise SystemExit(main())
