from __future__ import annotations

from collections import Counter
from itertools import combinations
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package
from hangboard_vectorizer.board_library import _CanonicalPackageRunner
from hangboard_vectorizer.display_paths import parse_display_path
from hangboard_vectorizer.vector_smoothing import rasterize_display_path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "trango-rock-prodigy-pivot"
EXPECTED_HOLDS = (
    ("upper-sloped-crimp-left", "edge", None, None),
    ("upper-sloped-crimp-right", "edge", None, None),
    ("outer-sloped-crimp-left", "edge", None, None),
    ("outer-sloped-crimp-right", "edge", None, None),
    ("variable-edge-left", "edge", (16, 31), None),
    ("variable-edge-right", "edge", (16, 31), None),
    ("medium-crimp-left", "edge", (9, 10), None),
    ("medium-crimp-right", "edge", (9, 10), None),
    ("large-crimp-left", "edge", (11, 12), None),
    ("large-crimp-right", "edge", (11, 12), None),
    ("two-finger-pocket-left", "pocket", (28, 32), 2),
    ("two-finger-pocket-right", "pocket", (28, 32), 2),
    ("three-finger-pocket-left", "pocket", (17, 28), 3),
    ("three-finger-pocket-right", "pocket", (17, 28), 3),
    ("outer-wedge-pinch-left", "pinch", None, None),
    ("outer-wedge-pinch-right", "pinch", None, None),
    ("lower-sloper-left", "sloper", None, None),
    ("lower-sloper-right", "sloper", None, None),
)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index][0], EXPECTED_HOLDS[index + 1][0])
    for index in range(0, len(EXPECTED_HOLDS), 2)
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_trango_rock_prodigy_pivot_preserves_numbered_physical_inventory() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board.id == "trango.rock-prodigy-pivot"
    assert board.manufacturer == "Trango"
    assert board.name == "Rock Prodigy Pivot"
    assert board.facts["dimensions"] == "15.5 × 5 × 2.5 in"
    assert math.isclose(board.facts["aspectRatio"], 3.1, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert Counter(hold.kind for hold in board.holds) == {
        "edge": 10,
        "pocket": 4,
        "pinch": 2,
        "sloper": 2,
    }
    assert sum(len(hold.geometry) for hold in board.holds) == 22

    actual_holds = tuple(
        (
            hold.id,
            hold.kind,
            (
                None
                if hold.depth_range_millimeters is None
                else (
                    hold.depth_range_millimeters.lower_bound,
                    hold.depth_range_millimeters.upper_bound,
                )
            ),
            hold.finger_capacity,
        )
        for hold in board.holds
    )
    assert actual_holds == EXPECTED_HOLDS
    assert {
        hold.id: len(hold.geometry)
        for hold in board.holds
        if len(hold.geometry) != 1
    } == {
        "outer-wedge-pinch-left": 2,
        "outer-wedge-pinch-right": 2,
        "lower-sloper-left": 2,
        "lower-sloper-right": 2,
    }

    for hold in board.holds:
        assert hold.size_millimeters is None
        assert hold.grip_type is None
        assert hold.features is None
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            commands = tuple(command.command for command in piece.shape.commands)
            assert commands[0] == "move"
            assert commands[-1] == "close"
            assert len(commands[1:-1]) >= 4
            assert set(commands[1:-1]) == {"curve"}
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        left_geometry = holds[left_id].geometry
        right_geometry = holds[right_id].geometry
        assert len(right_geometry) == len(left_geometry)
        for left, right in zip(left_geometry, right_geometry, strict=True):
            assert math.isclose(
                right.frame.x,
                1 - left.frame.x - left.frame.width,
                abs_tol=1e-12,
            )
            assert right.frame.y == left.frame.y
            assert right.frame.width == left.frame.width
            assert right.frame.height == left.frame.height
            assert right.treatment == left.treatment
            for left_command, right_command in zip(
                left.shape.commands, right.shape.commands, strict=True
            ):
                assert left_command.command == right_command.command
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                    assert math.isclose(right_y, left_y, abs_tol=1e-12)

    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as asset:
        width, height = asset.size
    piece_masks: list[tuple[str, np.ndarray]] = []
    for hold in board.holds:
        for piece_index, piece in enumerate(hold.geometry):
            piece_id = f"{hold.id}.geometry[{piece_index}]"
            display_path = parse_display_path(
                _CanonicalPackageRunner._piece_path(piece, width, height),
                piece_id,
                width,
                height,
            )
            assert display_path is not None
            mask = rasterize_display_path(display_path, width, height).astype(bool)
            piece_masks.append((piece_id, mask))
    assert len(piece_masks) == 22
    for (left_id, left_mask), (right_id, right_mask) in combinations(piece_masks, 2):
        overlap_pixels = np.count_nonzero(left_mask & right_mask)
        assert overlap_pixels == 0, (
            f"{left_id} overlaps {right_id} by {overlap_pixels} pixels"
        )

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {
        "cueStyle",
        "semantics",
        "evidence",
        "artwork",
        "catalog",
        "claims",
        "ui",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(child) for child in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(child) for child in value))
        return set()

    assert forbidden.isdisjoint(keys(raw))
