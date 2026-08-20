"""Independently audit hold-shape-only changes between catalog revisions."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PIL import Image

from .board_path_simplification import measure_native_contour_error

Point = tuple[float, float]

_WORKBENCH_GEOMETRY_PATH = (
    Path(__file__).resolve().parents[3] / "HangboardWorkbench" / "board_geometry.py"
)
_WORKBENCH_SPEC = importlib.util.spec_from_file_location(
    "hangboard_shape_audit_workbench_geometry", _WORKBENCH_GEOMETRY_PATH
)
if _WORKBENCH_SPEC is None or _WORKBENCH_SPEC.loader is None:
    raise ImportError("Hangboard Workbench geometry codec is unavailable")
_WORKBENCH_GEOMETRY = importlib.util.module_from_spec(_WORKBENCH_SPEC)
sys.modules[_WORKBENCH_SPEC.name] = _WORKBENCH_GEOMETRY
_WORKBENCH_SPEC.loader.exec_module(_WORKBENCH_GEOMETRY)
display_path_for_shape = _WORKBENCH_GEOMETRY.display_path_for_shape


def audit_board_documents(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    """Verify and measure shape-only reductions in one board document."""
    if _without(before, "holds") != _without(after, "holds"):
        raise ValueError("board non-shape fields changed")
    before_holds = before.get("holds")
    after_holds = after.get("holds")
    if not isinstance(before_holds, list) or not isinstance(after_holds, list):
        raise ValueError("board holds must be lists")
    if len(before_holds) != len(after_holds):
        raise ValueError("hold inventory changed")

    changes: list[dict[str, Any]] = []
    piece_count = 0
    for before_hold, after_hold in zip(before_holds, after_holds, strict=True):
        if _without(before_hold, "geometry") != _without(after_hold, "geometry"):
            raise ValueError("hold non-shape fields changed")
        before_pieces = before_hold.get("geometry")
        after_pieces = after_hold.get("geometry")
        if not isinstance(before_pieces, list) or not isinstance(after_pieces, list):
            raise ValueError("hold geometry must be lists")
        if len(before_pieces) != len(after_pieces):
            raise ValueError("piece inventory changed")
        piece_count += len(before_pieces)
        for piece_index, (before_piece, after_piece) in enumerate(
            zip(before_pieces, after_pieces, strict=True)
        ):
            if _without(before_piece, "shape") != _without(after_piece, "shape"):
                raise ValueError("piece non-shape fields changed")
            before_shape = before_piece.get("shape")
            after_shape = after_piece.get("shape")
            if before_shape == after_shape:
                continue
            if not isinstance(before_shape, Mapping) or not isinstance(after_shape, Mapping):
                raise ValueError("changed shapes must be objects")
            if before_shape.get("type") != "path" or after_shape.get("type") != "roundedRect":
                raise ValueError("shape change is not a path-to-primitive reduction")
            before_points = _editable_points(before_shape)
            after_points = _editable_points(after_shape)
            if before_points <= 0 or after_points != 0:
                raise ValueError("shape change did not reduce editable points to zero")
            frame = before_piece.get("frame")
            if not isinstance(frame, Mapping):
                raise ValueError("piece frame must be an object")
            before_contour = _render(frame, before_shape, width=width, height=height)
            after_contour = _render(frame, after_shape, width=width, height=height)
            error = measure_native_contour_error(
                before_contour,
                after_contour,
                width=width,
                height=height,
            )
            if error.maximum_boundary_deviation_pixels > 1.0:
                raise ValueError("shape change exceeds exact boundary limit")
            if error.symmetric_difference_ratio > 0.0025:
                raise ValueError("shape change exceeds symmetric difference limit")
            changes.append(
                {
                    "holdId": before_hold["id"],
                    "pieceIndex": piece_index,
                    "beforeType": "path",
                    "afterType": "roundedRect",
                    "beforeEditablePoints": before_points,
                    "afterEditablePoints": after_points,
                    "maximumBoundaryDeviationPixels": error.maximum_boundary_deviation_pixels,
                    "symmetricDifferenceRatio": error.symmetric_difference_ratio,
                }
            )
    return {
        "boardId": before["id"],
        "holdCount": len(before_holds),
        "pieceCount": piece_count,
        "changedPieces": changes,
    }


def audit_revisions(
    repository_root: Path,
    *,
    before_ref: str,
    after_root: Path,
) -> dict[str, Any]:
    """Compare an explicit git revision with an explicit filesystem root."""
    before_files = _git_paths(repository_root, before_ref)
    after_files = {
        path.relative_to(after_root).as_posix()
        for path in (after_root / "Hangboards").rglob("*")
        if path.is_file() and path.name != ".workbench.lock"
    }
    if before_files != after_files:
        raise ValueError("catalog file inventory changed")

    board_paths = sorted(path for path in before_files if path.endswith("/board.json"))
    reports: list[dict[str, Any]] = []
    for relative_path in sorted(before_files):
        before_bytes = _git_bytes(repository_root, before_ref, relative_path)
        after_bytes = (after_root / relative_path).read_bytes()
        if not relative_path.endswith("/board.json") and before_bytes != after_bytes:
            raise ValueError(f"non-board file changed: {relative_path}")
    for board_path in board_paths:
        before = json.loads(_git_bytes(repository_root, before_ref, board_path))
        after = json.loads((after_root / board_path).read_text(encoding="utf-8"))
        asset_path = after["presentation"]["assetPath"]
        with Image.open((after_root / board_path).parent / asset_path) as image:
            width, height = image.size
        reports.append(
            audit_board_documents(before, after, width=width, height=height)
        )
    changes = [
        {"boardId": report["boardId"], **piece}
        for report in reports
        for piece in report["changedPieces"]
    ]
    return {
        "beforeRef": before_ref,
        "afterRoot": str(after_root.resolve()),
        "boardCount": len(reports),
        "holdCount": sum(report["holdCount"] for report in reports),
        "pieceCount": sum(report["pieceCount"] for report in reports),
        "changedPieceCount": len(changes),
        "removedEditablePoints": sum(
            piece["beforeEditablePoints"] - piece["afterEditablePoints"]
            for piece in changes
        ),
        "changedPieces": changes,
    }


def _without(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    result.pop(key, None)
    return result


def _editable_points(shape: Mapping[str, Any]) -> int:
    commands = shape.get("commands", ())
    if not isinstance(commands, Sequence):
        return 0
    return sum(
        int(field in command)
        for command in commands
        if isinstance(command, Mapping)
        for field in ("to", "control", "control1", "control2")
    )


def _render(
    frame: Mapping[str, Any],
    shape: Mapping[str, Any],
    *,
    width: int,
    height: int,
) -> list[Point]:
    contour = list(
        display_path_for_shape(
            frame,
            shape,
            width,
            height,
            label="independent shape audit",
        ).contour
    )
    if len(contour) > 1 and contour[0] == contour[-1]:
        contour.pop()
    return contour


def _git_paths(repository_root: Path, revision: str) -> set[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", revision, "--", "Hangboards"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def _git_bytes(repository_root: Path, revision: str, relative_path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=repository_root,
        check=True,
        capture_output=True,
    ).stdout


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hangboard_packages.board_shape_change_audit")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--before-ref", required=True)
    parser.add_argument("--after-root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    print(
        json.dumps(
            audit_revisions(
                arguments.repository_root,
                before_ref=arguments.before_ref,
                after_root=arguments.after_root,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
