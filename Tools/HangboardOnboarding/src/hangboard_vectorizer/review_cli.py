"""CLI for hold-region review artifact inspection."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from .review_acceptance import validate_acceptance, write_acceptance
from .review_artifacts import discover_review_run, inspect_run
from .review_lint import lint_report_payload, lint_review, write_lint_report
from .review_preview import render_preview_bundle, write_comparison_document


def main(argv: Sequence[str] | None = None) -> int:
    """Run one review command and return a process-style exit code."""
    try:
        arguments = _parser().parse_args(argv)
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

    lint = subcommands.add_parser("lint", help="lint edited review artifacts")
    lint.add_argument("--run", type=Path, required=True, help="review run directory")
    lint.add_argument(
        "--json",
        action="store_true",
        help="print compact JSON output (default behavior)",
    )

    preview = subcommands.add_parser(
        "preview", help="render deterministic review preview artifacts"
    )
    preview.add_argument("--run", type=Path, required=True, help="review run directory")
    preview.add_argument(
        "--output", type=Path, required=True, help="workspace-owned preview output root"
    )
    preview.add_argument(
        "--json",
        action="store_true",
        help="print compact JSON output (default behavior)",
    )

    compare = subcommands.add_parser(
        "compare", help="write a self-contained read-only comparison document"
    )
    compare.add_argument("--run", type=Path, required=True, help="review run directory")
    compare.add_argument(
        "--output", type=Path, required=True, help="generated comparison HTML path"
    )
    compare.add_argument(
        "--json",
        action="store_true",
        help="print compact JSON output (default behavior)",
    )

    accept = subcommands.add_parser("accept", help="record an acceptance decision")
    accept.add_argument("--run", type=Path, required=True, help="review run directory")
    accept.add_argument(
        "--decision",
        choices=("accepted", "rejected", "needs-changes"),
        required=True,
        help="acceptance decision to record",
    )
    accept.add_argument(
        "--reviewer",
        default="local-user",
        help="reviewer name to record (default: local-user)",
    )
    accept.add_argument("--notes", required=True, help="review notes to record")
    return parser


def _run(arguments: argparse.Namespace) -> tuple[dict[str, object], int]:
    run = discover_review_run(arguments.run)
    if arguments.command == "inspect":
        return inspect_run(run), 0
    if arguments.command == "lint":
        report = lint_review(run)
        write_lint_report(run, report)
        return lint_report_payload(report), (0 if report.passed else 1)
    if arguments.command == "preview":
        return render_preview_bundle(run, arguments.output), 0
    if arguments.command == "compare":
        output = arguments.output.resolve(strict=False)
        if run.edited_regions is None:
            return {
                "output": str(output),
                "reason": "edited regions artifact is missing",
            }, 2
        path = write_comparison_document(run, output)
        return {"output": str(path)}, 0
    if arguments.command == "accept":
        if arguments.decision == "accepted":
            report = lint_review(run)
            write_lint_report(run, report)
            if not report.passed:
                raise ValueError("lint must pass before acceptance")
        path = write_acceptance(
            run,
            arguments.decision,
            arguments.reviewer,
            arguments.notes,
        )
        record = validate_acceptance(discover_review_run(run.root))
        return _acceptance_payload(record, path), 0
    raise ValueError(f"unsupported command: {arguments.command}")


def _acceptance_payload(record, path: Path) -> dict[str, object]:
    return {
        "decision": record.decision,
        "notes": record.notes,
        "path": str(path),
        "reviewedAt": record.reviewedAt,
        "reviewer": record.reviewer,
        "schemaVersion": record.schemaVersion,
        "source": record.source,
        "toolVersion": record.toolVersion,
    }


def _first_line(error: BaseException) -> str:
    message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
    return message


if __name__ == "__main__":
    raise SystemExit(main())
