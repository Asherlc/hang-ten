from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

import pytest
from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "target10a-linebreaker-base"
EXPECTED_HOLDS = (
    ("jug-left", "jug", None, None, None, 1),
    ("sloper-32-5-left", "sloper", None, None, "sloper", 1),
    ("sloper-22-5-center", "sloper", None, None, "sloper", 1),
    ("sloper-32-5-right", "sloper", None, None, "sloper", 1),
    ("jug-right", "jug", None, None, None, 1),
    ("edge-16-left", "edge", 16, 4, None, 1),
    ("pocket-28-left", "pocket", 28, 3, "threeFingerPocket", 1),
    ("pocket-28-right", "pocket", 28, 3, "threeFingerPocket", 1),
    ("edge-16-right", "edge", 16, 4, None, 1),
    ("pocket-37-left", "pocket", 37, 4, "fourFingerPocket", 1),
    ("pocket-45-left", "pocket", 45, 3, "threeFingerPocket", 1),
    ("pocket-50-left", "pocket", 50, 2, "twoFingerPocket", 1),
    ("sloper-bar-35-center", "sloper", 35, None, "sloper", 1),
    ("pocket-50-right", "pocket", 50, 2, "twoFingerPocket", 1),
    ("pocket-45-right", "pocket", 45, 3, "threeFingerPocket", 1),
    ("pocket-37-right", "pocket", 37, 4, "fourFingerPocket", 1),
    ("pocket-30-left", "pocket", 30, 2, "twoFingerPocket", 1),
    ("pocket-24-left", "pocket", 24, 2, "twoFingerPocket", 1),
    ("edge-20-left", "edge", 20, 4, None, 1),
    ("edge-18-left", "edge", 18, 3, None, 1),
    ("edge-18-right", "edge", 18, 3, None, 1),
    ("edge-20-right", "edge", 20, 4, None, 1),
    ("pocket-24-right", "pocket", 24, 2, "twoFingerPocket", 1),
    ("pocket-30-right", "pocket", 30, 2, "twoFingerPocket", 1),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-32-5-left", "sloper-32-5-right"),
    ("edge-16-left", "edge-16-right"),
    ("pocket-28-left", "pocket-28-right"),
    ("pocket-37-left", "pocket-37-right"),
    ("pocket-45-left", "pocket-45-right"),
    ("pocket-50-left", "pocket-50-right"),
    ("pocket-30-left", "pocket-30-right"),
    ("pocket-24-left", "pocket-24-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-18-left", "edge-18-right"),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_exact_global_mirror(left: object, right: object) -> None:
    assert right.frame.x == pytest.approx(
        1 - left.frame.x - left.frame.width, abs=1e-12
    )
    assert right.frame.y == pytest.approx(left.frame.y, abs=1e-12)
    assert right.frame.width == pytest.approx(left.frame.width, abs=1e-12)
    assert right.frame.height == pytest.approx(left.frame.height, abs=1e-12)
    assert right.treatment == left.treatment
    assert [command.command for command in right.shape.commands] == [
        command.command for command in left.shape.commands
    ]
    for left_command, right_command in zip(
        left.shape.commands, right.shape.commands, strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def test_target10a_linebreaker_base_preserves_the_manufacturer_hold_map() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "target10a-linebreaker-base"
    assert board.manufacturer == "target10a"
    assert board.name == "Linebreaker BASE"
    assert board.facts["dimensions"] == "58 × 15 × 5.5 cm"
    assert math.isclose(board.facts["aspectRatio"], 58 / 15, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (
            hold.id,
            hold.kind,
            hold.size_millimeters,
            hold.finger_capacity,
            hold.grip_type,
            len(hold.geometry),
        )
        for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "jug": 2,
        "sloper": 4,
        "edge": 6,
        "pocket": 12,
    }
    assert sum(len(hold.geometry) for hold in board.holds) == 24

    for hold in board.holds:
        assert hold.depth_range_millimeters is None
        assert hold.features is None
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert any(command.command == "curve" for command in piece.shape.commands)
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_exact_global_mirror(
            holds[left_id].geometry[0], holds[right_id].geometry[0]
        )

    for center_id in ("sloper-22-5-center", "sloper-bar-35-center"):
        center = holds[center_id].geometry[0].frame
        assert center.x + center.width / 2 == pytest.approx(0.5, abs=1e-12)


def test_target10a_linebreaker_base_is_a_closed_direct_child_package() -> None:
    package_entries = {path.name for path in PACKAGE_ROOT.iterdir()}
    asset_entries = {path.name for path in (PACKAGE_ROOT / "assets").iterdir()}
    assert package_entries == {"board.json", "assets"}
    assert asset_entries == {"primary.png"}

    document = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden_keys = {
        "artwork",
        "claims",
        "cueStyle",
        "evidence",
        "semantics",
        "sourceAudit",
        "ui",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(document))


def test_target10a_linebreaker_base_keeps_32_5_slopers_on_the_visible_full_canvas_plane() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    raster_width, raster_height = Image.open(
        PACKAGE_ROOT / "assets" / "primary.png"
    ).size
    holds = {hold.id: hold for hold in board.holds}

    assert (raster_width, raster_height) == (1448, 1086)
    for hold_id in ("sloper-32-5-left", "sloper-32-5-right"):
        piece = holds[hold_id].geometry[0]
        assert round(piece.frame.y * raster_height) == 387
        assert round((piece.frame.y + piece.frame.height) * raster_height) == 441
