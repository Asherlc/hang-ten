from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "escape-unlimited-7"
EXPECTED_HOLDS = (
    ("top-sloper-60", "sloper", 60),
    ("edge-45-left", "edge", 45),
    ("edge-45-right", "edge", 45),
    ("edge-20-left", "edge", 20),
    ("edge-20-right", "edge", 20),
    ("edge-15-left", "edge", 15),
    ("edge-15-right", "edge", 15),
)
MIRRORED_PAIRS = (
    ("edge-45-left", "edge-45-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-15-left", "edge-15-right"),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_escape_unlimited_7_preserves_audited_inventory_and_mirrored_edges() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "escape-unlimited-7"
    assert board.manufacturer == "Escape Climbing"
    assert board.name == "Unlimited Board"
    assert board.facts["dimensions"] == "23.75 × 7.25 × 1.875 in"
    assert board.facts["aspectRatio"] == pytest.approx(23.75 / 7.25)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {"edge": 6, "sloper": 1}

    for hold in board.holds:
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert len(piece.shape.commands) >= 8
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0
        assert piece.treatment is None
        assert hold.depth_range_millimeters is None
        assert hold.grip_type is None
        assert hold.finger_capacity is None
        assert hold.features is None

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
        assert right.frame.x == pytest.approx(1 - left.frame.x - left.frame.width)
        assert right.frame.y == pytest.approx(left.frame.y)
        assert right.frame.width == pytest.approx(left.frame.width)
        assert right.frame.height == pytest.approx(left.frame.height)
        assert [command.command for command in right.shape.commands] == [
            command.command for command in left.shape.commands
        ]
        for left_command, right_command in zip(
            left.shape.commands, right.shape.commands, strict=True
        ):
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert right_x == pytest.approx(1 - left_x)
                assert right_y == pytest.approx(left_y)

    crown = holds["top-sloper-60"].geometry[0]
    assert crown.frame.x == pytest.approx(1 - crown.frame.x - crown.frame.width)
    assert crown.frame.width > 0.8
