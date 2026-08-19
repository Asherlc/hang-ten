"""Command-line entry point for hangboard package discovery."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .board_catalog import BoardInventory, BoardPackage, discover_board_packages
from .board_path_simplification import simplify_package_hold_paths
from .board_presentation import normalize_package_presentation


class _CliError(ValueError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        if arguments.command in {"validate", "status"}:
            inventory = discover_board_packages(
                arguments.root,
                require_complete_inventory=arguments.final_inventory,
            )
            print(_status_payload(inventory))
            return 0
        if arguments.command == "simplify-hold-paths":
            inventory = discover_board_packages(arguments.root)
            payload, failed = _simplification_payload(inventory, write=arguments.write)
            print(payload)
            return 1 if failed else 0
        if arguments.command == "normalize-presentations":
            inventory = discover_board_packages(arguments.root)
            payload, failed = _presentation_payload(inventory, write=arguments.write)
            print(payload)
            return 1 if failed else 0
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
    simplify = subcommands.add_parser(
        "simplify-hold-paths",
        help="reduce validated hold-path editable points within native-pixel error limits",
    )
    simplify.add_argument("--root", type=Path, required=True)
    simplify.add_argument("--write", action="store_true", help="atomically update changed board.json files")
    normalize = subcommands.add_parser(
        "normalize-presentations",
        help="tightly crop presentation canvases and exactly reproject hold frames",
    )
    normalize.add_argument("--root", type=Path, required=True)
    normalize.add_argument("--write", action="store_true", help="atomically update changed board packages")
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


def _simplification_payload(inventory: BoardInventory, *, write: bool) -> tuple[str, bool]:
    boards = []
    failed = False
    for package in inventory.packages:
        try:
            result = simplify_package_hold_paths(package.root, write=write)
        except (OSError, ValueError) as error:
            failed = True
            boards.append(_package_error(package, error))
            continue
        boards.append(_simplification_board_payload(package, result))
    return _catalog_payload(boards, inventory, write=write), failed


def _presentation_payload(inventory: BoardInventory, *, write: bool) -> tuple[str, bool]:
    boards = []
    failed = False
    for package in inventory.packages:
        try:
            result = normalize_package_presentation(package.root, write=write)
        except (OSError, ValueError) as error:
            failed = True
            boards.append(_package_error(package, error))
            continue
        boards.append(
            {
                "id": result.board_id,
                "path": package.root.name,
                "originalDimensions": [result.original_width, result.original_height],
                "newDimensions": [result.width, result.height],
                "crop": list(result.crop),
                "holdCount": result.hold_count,
                "changed": result.changed,
            }
        )
    return _catalog_payload(boards, inventory, write=write), failed


def _catalog_payload(
    boards: list[dict[str, object]], inventory: BoardInventory, *, write: bool
) -> str:
    return json.dumps(
        {
            "boards": boards,
            "draftCount": len(inventory.drafts),
            "drafts": [path.name for path in inventory.drafts],
            "write": write,
        },
        indent=2,
        sort_keys=True,
    )


def _package_error(package: BoardPackage, error: Exception) -> dict[str, object]:
    message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
    return {"id": package.board.id, "path": package.root.name, "error": message}


def _simplification_board_payload(package: BoardPackage, result: object) -> dict[str, object]:
    return {
        "id": result.board_id,
        "path": package.root.name,
        "changed": result.changed,
        "pieces": [
            {
                "holdId": piece.hold_id,
                "pieceIndex": piece.piece_index,
                "beforeEditablePoints": piece.before_editable_points,
                "afterEditablePoints": piece.after_editable_points,
                "maximumBoundaryDeviationPixels": piece.maximum_boundary_deviation_pixels,
                "symmetricDifferenceRatio": piece.symmetric_difference_ratio,
                "changed": piece.changed,
            }
            for piece in result.pieces
            if piece.changed
        ],
        "skippedPieces": [
            {
                "holdId": piece.hold_id,
                "pieceIndex": piece.piece_index,
                "beforeEditablePoints": piece.before_editable_points,
                "afterEditablePoints": piece.after_editable_points,
                "reason": "exactHausdorffComplexityCap",
            }
            for piece in result.pieces
            if piece.complexity_capped
        ],
        "coverage": {
            "eligible": sum(piece.eligible_candidates for piece in result.pieces),
            "evaluated": sum(piece.evaluated_candidates for piece in result.pieces),
            "rejected": sum(piece.rejected_candidates for piece in result.pieces),
            "unsupported": sum(piece.unsupported_pieces for piece in result.pieces),
            "skipped": sum(piece.complexity_capped for piece in result.pieces),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
