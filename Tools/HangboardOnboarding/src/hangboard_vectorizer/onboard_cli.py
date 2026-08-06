"""Command-line interface for the approval-aware onboarding runner."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

import cv2

from .onboarding_run import (
    OnboardingStateError,
    approve_stage,
    read_status,
    resume_run,
    start_run,
)
from .workspace_paths import default_workspace_root, resolve_workspace_path


class _CliError(ValueError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    """Run one onboarding action and return a process-style exit code."""
    try:
        arguments = _parser().parse_args(argv)
        _validate(arguments)
        result = _run(arguments)
    except SystemExit as error:
        return int(error.code or 0)
    except _CliError as error:
        print(f"error: {_first_line(error)}", file=sys.stderr)
        return 2
    except (OSError, ValueError, cv2.error) as error:
        print(f"error: {_first_line(error)}", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hangboard-onboard",
        description="Create and approve a resumable commercial-product onboarding run.",
    )
    parser.add_argument("--product-name", help="caller-asserted commercial product name")
    parser.add_argument("--source", help="local image path or HTTP(S) image URL")
    parser.add_argument("--output", type=Path, required=True, help="onboarding run directory")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=default_workspace_root(),
        help=(
            "owned root for generated artifacts "
            "(default: $HANGBOARD_WORKSPACE_ROOT or .context/hangboard-onboarding)"
        ),
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--approve", choices=("stage-0", "stage-1", "stage-2", "stage-3", "stage-4"), help="approve a reviewed stage")
    actions.add_argument("--resume", action="store_true", help="run the next installed stage")
    actions.add_argument("--status", action="store_true", help="validate and print run status")
    return parser


def _validate(arguments: argparse.Namespace) -> None:
    action = arguments.approve or ("resume" if arguments.resume else "status" if arguments.status else "start")
    has_start_values = arguments.product_name is not None or arguments.source is not None
    if action == "start":
        if arguments.product_name is None or arguments.source is None:
            raise _CliError("--product-name and --source are required when starting a run")
    elif has_start_values:
        raise _CliError("--product-name and --source are valid only when starting a run")
    arguments.workspace_root = arguments.workspace_root.resolve(strict=False)
    try:
        arguments.output = resolve_workspace_path(arguments.output, arguments.workspace_root)
    except ValueError as error:
        raise _CliError(str(error)) from error


def _run(arguments: argparse.Namespace):
    if arguments.approve:
        return approve_stage(arguments.output, int(arguments.approve.removeprefix("stage-")))
    if arguments.resume:
        return resume_run(arguments.output)
    if arguments.status:
        return read_status(arguments.output)
    return start_run(
        arguments.product_name,
        arguments.source,
        arguments.output,
        workspace_root=arguments.workspace_root,
    )


def _first_line(error: BaseException) -> str:
    message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
    return message


if __name__ == "__main__":
    raise SystemExit(main())
