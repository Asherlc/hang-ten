#!/usr/bin/env python3
"""Generate the app's board library from canonical hangboard manifests."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping


_LEGACY_GRIP_TYPE_FINGER_CAPACITY = {
    "sloper": 4,
    "fourFingerPocket": 4,
    "threeFingerPocket": 3,
    "twoFingerPocket": 2,
}
_APP_HOLD_FIELDS = (
    "id",
    "name",
    "shortLabel",
    "detail",
    "kind",
    "frame",
    "sizeMillimeters",
    "gripType",
    "fingerCapacity",
    "features",
)


def load_board_catalog_module(repo_root: Path):
    module_path = (
        repo_root
        / "Tools"
        / "HangboardPipeline"
        / "src"
        / "hangboard_vectorizer"
        / "board_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("board_library_export", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load board catalog module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"{description} does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{description} is not valid JSON: {path}") from error
    except OSError as error:
        raise ValueError(f"cannot read {description}: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{description} must be a JSON object: {path}")
    return payload


def existing_boards_by_id(library: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    boards = library.get("boards")
    if not isinstance(boards, list):
        raise ValueError("board library boards must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for index, board in enumerate(boards):
        if not isinstance(board, Mapping):
            raise ValueError(f"board library boards[{index}] must be an object")
        board_id = board.get("id")
        if not isinstance(board_id, str) or not board_id:
            raise ValueError(f"board library boards[{index}].id must be a non-empty string")
        if board_id in result:
            raise ValueError(f"board library contains duplicate board id {board_id!r}")
        result[board_id] = board
    return result


def existing_holds_by_id(board: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    holds = board.get("holds", [])
    if not isinstance(holds, list):
        raise ValueError(f"board library board {board['id']!r} holds must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for index, hold in enumerate(holds):
        if not isinstance(hold, Mapping):
            raise ValueError(f"board library board {board['id']!r} holds[{index}] must be an object")
        hold_id = hold.get("id")
        if not isinstance(hold_id, str) or not hold_id:
            raise ValueError(f"board library board {board['id']!r} holds[{index}].id must be a non-empty string")
        if hold_id in result:
            raise ValueError(f"board library board {board['id']!r} contains duplicate hold id {hold_id!r}")
        result[hold_id] = hold
    return result


def app_hold(hold: Any, existing_hold: Mapping[str, Any] | None) -> dict[str, Any]:
    canonical = hold.to_json()
    payload = {field: canonical[field] for field in _APP_HOLD_FIELDS if field in canonical}
    grip_type = payload.get("gripType")
    if grip_type in _LEGACY_GRIP_TYPE_FINGER_CAPACITY:
        payload["fingerCapacity"] = _LEGACY_GRIP_TYPE_FINGER_CAPACITY[grip_type]
    if existing_hold is not None and "cueStyle" in existing_hold:
        payload["cueStyle"] = existing_hold["cueStyle"]
    return payload


def validate_semantic_holds(
    board_id: str,
    semantic_holds: Any,
    generated_hold_ids: set[str],
) -> None:
    if not isinstance(semantic_holds, Mapping):
        raise ValueError(f"board library board {board_id!r} semanticHolds must be an object")
    for semantic_name, semantic_hold in semantic_holds.items():
        if not isinstance(semantic_hold, Mapping):
            raise ValueError(
                f"board library board {board_id!r} semanticHolds.{semantic_name}."
                "holdIDs must be a list of strings"
            )
        hold_ids = semantic_hold.get("holdIDs")
        if not isinstance(hold_ids, list) or any(
            not isinstance(hold_id, str) for hold_id in hold_ids
        ):
            raise ValueError(
                f"board library board {board_id!r} semanticHolds.{semantic_name}."
                "holdIDs must be a list of strings"
            )
        missing_hold_ids = sorted(set(hold_ids) - generated_hold_ids)
        if missing_hold_ids:
            raise ValueError(
                f"board library board {board_id!r} semanticHolds.{semantic_name}."
                f"holdIDs references missing generated holds: {missing_hold_ids}"
            )


def app_board(board: Any, existing_board: Mapping[str, Any]) -> dict[str, Any]:
    existing_holds = existing_holds_by_id(existing_board)
    canonical_fields = {
        "id": board.id,
        "manufacturer": board.manufacturer,
        "name": board.name,
        "dimensions": board.dimensions,
        "aspectRatio": board.aspect_ratio,
        "productURL": board.product_url,
    }
    payload = {
        key: value
        for key, value in existing_board.items()
        if key not in {*canonical_fields, "holds"}
    }
    payload.update(canonical_fields)
    payload["holds"] = [
        app_hold(hold, existing_holds.get(hold.id))
        for hold in board.holds
    ]
    if "semanticHolds" in payload:
        validate_semantic_holds(
            board.id,
            payload["semanticHolds"],
            {hold["id"] for hold in payload["holds"]},
        )
    return payload


def render_board_library(catalog_path: Path, library_path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    board_catalog = load_board_catalog_module(repo_root)
    catalog = board_catalog.validate_catalog(catalog_path)
    existing_library = load_json_object(library_path, "board library")
    existing_boards = existing_boards_by_id(existing_library)
    catalog_root = catalog_path.parent.resolve(strict=False)

    boards = []
    for entry in sorted(catalog.boards, key=lambda candidate: candidate.id):
        existing_board = existing_boards.get(entry.id)
        if existing_board is None:
            raise ValueError(
                f"board library is missing app metadata for canonical board {entry.id!r}"
            )
        board = board_catalog.load_board(catalog_root / entry.path)
        boards.append(app_board(board, existing_board))

    rendered_library = dict(existing_library)
    rendered_library["boards"] = boards
    return json.dumps(rendered_library, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the checked-in app board library.")
    parser.add_argument("--check", action="store_true", help="fail if the board library is stale")
    parser.add_argument("--catalog", type=Path, help="canonical catalog JSON to export")
    parser.add_argument("--output", type=Path, help="board library JSON to regenerate or check")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    catalog_path = args.catalog or repo_root / "Hangboards" / "catalog.json"
    output_path = args.output or repo_root / "HangTen" / "Resources" / "BoardLibrary.json"

    try:
        rendered = render_board_library(catalog_path, output_path)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    current = output_path.read_text(encoding="utf-8")
    if args.check:
        if current != rendered:
            print(
                f"Board library drift detected for {output_path}; run scripts/export-board-library.py",
                file=sys.stderr,
            )
            return 1
        return 0

    if current != rendered:
        output_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
