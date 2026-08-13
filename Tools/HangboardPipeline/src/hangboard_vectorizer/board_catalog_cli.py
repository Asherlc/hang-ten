"""Command-line entry point for hangboard catalog tooling."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .board_catalog import (
    CatalogBoardEntry,
    CatalogDocument,
    load_board,
    register_run,
    validate_catalog,
)


class _CliError(ValueError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        if arguments.command == "validate":
            catalog = validate_catalog(arguments.catalog)
            print(_status_payload(catalog=catalog, catalog_path=arguments.catalog))
            return 0
        if arguments.command == "status":
            catalog = validate_catalog(arguments.catalog)
            print(_status_payload(catalog=catalog, catalog_path=arguments.catalog))
            return 0
        if arguments.command == "register":
            board = register_run(
                catalog_path=arguments.catalog,
                board_id=arguments.board,
                run_path=arguments.run,
                run_id=arguments.run_id,
            )
            print(
                json.dumps(
                    {
                        "id": board.id,
                        "lifecycle": board.lifecycle,
                        "runCount": len(board.onboarding_runs),
                        "regionCount": sum(run.region_count for run in board.onboarding_runs),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        raise _CliError("unknown command")
    except SystemExit as error:
        return int(error.code or 0)
    except _CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
        print(f"error: {message}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hangboard-catalog")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="validate a catalog and board packages")
    validate.add_argument("--catalog", type=Path, required=True)

    status = subcommands.add_parser("status", help="print catalog metadata and statuses")
    status.add_argument("--catalog", type=Path, required=True)

    register = subcommands.add_parser("register", help="copy a run into a board package")
    register.add_argument("--catalog", type=Path, required=True)
    register.add_argument("--board", required=True)
    register.add_argument("--run", type=Path, required=True)
    register.add_argument("--run-id")
    return parser


def _status_payload(catalog: CatalogDocument, catalog_path: Path) -> str:
    catalog_root = catalog_path.parent
    payload = {
        "boards": [
            _board_status(entry, catalog_root / entry.path) for entry in catalog.boards
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _board_status(entry: CatalogBoardEntry, board_path: Path) -> dict[str, object]:
    if not board_path.is_file():
        return {
            "id": entry.id,
            "path": entry.path,
            "lifecycle": entry.lifecycle,
            "onboardingRuns": [],
            "status": "missing",
        }
    board = load_board(board_path)
    return {
        "id": board.id,
        "path": entry.path,
        "lifecycle": board.lifecycle,
        "status": "ok",
        "onboardingRuns": [run.to_json() for run in board.onboarding_runs],
    }


if __name__ == "__main__":
    raise SystemExit(main())
