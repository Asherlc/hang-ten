"""CLI for hold-region promotion and safe apply."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from .promotion import promote_run, promotion_report_payload
from .promotion_profile import load_promotion_profile
from .review_artifacts import discover_review_run


def main(argv: Sequence[str] | None = None) -> int:
    """Run one promotion command and return a process-style exit code."""
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
        if arguments.command == "promote" and arguments.apply and arguments.profile is None:
            parser.error("--apply requires --profile")
        payload, exit_code = _run(arguments)
    except SystemExit as error:
        return int(error.code or 0)
    except (OSError, ValueError) as error:
        print(f"error: {_first_line(error)}", file=sys.stderr)
        return 3
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hangboard-promote",
        description="Promote accepted hold-region review artifacts safely.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    promote = subcommands.add_parser("promote", help="build a promotion package")
    promote.add_argument("--run", type=Path, required=True, help="review run directory")
    promote.add_argument("--profile", type=Path, help="promotion profile JSON path")
    promote.add_argument(
        "--repository-root",
        type=Path,
        required=True,
        help="repository root for confined promotion destinations",
    )
    promote.add_argument(
        "--apply",
        action="store_true",
        help="copy the planned package files into repository destinations",
    )
    promote.add_argument(
        "--json",
        action="store_true",
        help="print compact JSON output (default behavior)",
    )
    return parser


def _run(arguments: argparse.Namespace) -> tuple[dict[str, object], int]:
    if arguments.command != "promote":
        raise ValueError(f"unsupported command: {arguments.command}")
    run = discover_review_run(arguments.run)
    profile = (
        load_promotion_profile(arguments.profile)
        if arguments.profile is not None
        else None
    )
    report = promote_run(
        run,
        profile,
        arguments.repository_root,
        apply=arguments.apply,
    )
    exit_code = 0 if report.status in {"ready", "handoff-required"} else 3
    return promotion_report_payload(report), exit_code


def _first_line(error: BaseException) -> str:
    message = str(error)
    return message.splitlines()[0] if message else error.__class__.__name__


if __name__ == "__main__":
    raise SystemExit(main())
