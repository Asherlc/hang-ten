"""Command-line entry point for hangboard package discovery."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .board_catalog import BoardInventory, BoardPackage, discover_board_packages


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        inventory = discover_board_packages(
            arguments.root,
            require_complete_inventory=arguments.final_inventory,
        )
        print(_status_payload(inventory))
        return 0
    except SystemExit as error:
        return int(error.code or 0)
    except (OSError, ValueError) as error:
        message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
        print(f"error: {message}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hangboard-packages")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("validate", "validate discovered board packages"),
        ("status", "print discovered package metadata"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument(
            "--final-inventory",
            action="store_true",
            help="reject primary-only draft directories",
        )
    return parser


def _status_payload(inventory: BoardInventory) -> str:
    payload = {
        "boards": [_board_status(package) for package in inventory.packages],
        "drafts": [path.name for path in inventory.drafts],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _board_status(package: BoardPackage) -> dict[str, object]:
    return {
        "id": package.board.id,
        "path": package.root.name,
    }


if __name__ == "__main__":
    raise SystemExit(main())
