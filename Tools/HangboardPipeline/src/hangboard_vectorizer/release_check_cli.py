"""CLI entry point for repository-facing hold-region release checks."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from .release_check import (
    release_check_blockers,
    release_check_report,
    run_release_check,
)
from .review_artifacts import discover_review_run


def main(argv: Sequence[str] | None = None) -> int:
    """Run one release-check command and return a process-style exit code."""
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
        payload, exit_code = _run(arguments)
    except SystemExit as error:
        return int(error.code or 0)
    except (OSError, ValueError) as error:
        print(f"error: {_first_line(error)}", file=sys.stderr)
        return 2

    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hangboard-release-check",
        description="Run deterministic release checks for reviewed hangboard artifacts.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    release_check = subcommands.add_parser(
        "release-check", help="verify a promoted review run before release"
    )
    release_check.add_argument("--run", type=Path, required=True, help="review run directory")
    release_check.add_argument(
        "--repository-root",
        type=Path,
        required=True,
        help="repository root for export and destination checks",
    )
    release_check.add_argument(
        "--xcode",
        action="store_true",
        help="also run the shared HangTen XCTest command on an isolated simulator",
    )
    release_check.add_argument(
        "--json",
        action="store_true",
        help="print compact JSON output (default behavior)",
    )
    release_check.add_argument(
        "--explain",
        action="store_true",
        help="include machine-readable blockers and remediations when checks fail",
    )
    return parser


def _run(arguments: argparse.Namespace) -> tuple[dict[str, object], int]:
    if arguments.command != "release-check":
        raise ValueError(f"unsupported command: {arguments.command}")
    run = discover_review_run(arguments.run)
    if not arguments.repository_root.is_dir():
        raise ValueError(
            f"repository root must be a directory: {arguments.repository_root.resolve(strict=False)}"
        )
    results = run_release_check(
        run,
        arguments.repository_root,
        run_xcode=arguments.xcode,
    )
    payload = release_check_report(results)
    if arguments.explain:
        payload["blockers"] = release_check_blockers(results)
    return payload, 0 if payload["passed"] else 3


def _first_line(error: BaseException) -> str:
    message = str(error)
    return message.splitlines()[0] if message else error.__class__.__name__


if __name__ == "__main__":
    raise SystemExit(main())
