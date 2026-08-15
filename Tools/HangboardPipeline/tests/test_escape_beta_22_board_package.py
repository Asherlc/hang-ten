from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "escape-beta-22"
EXPECTED_HOLDS = tuple(
    (f"hold-{family:02d}-{side}", kind)
    for family, kind in (
        (1, "pinch"),
        (2, "pinch"),
        (3, "jug"),
        (4, "jug"),
        (5, "edge"),
        (6, "edge"),
        (7, "edge"),
        (8, "edge"),
        (9, "sloper"),
        (10, "sloper"),
        (11, "sloper"),
    )
    for side in ("left", "right")
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_escape_beta_22_audited_inventory_geometry_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "escape-beta-22"
    assert tuple((hold.id, hold.kind) for hold in board.holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "pinch": 4,
        "jug": 4,
        "edge": 8,
        "sloper": 6,
    }

    for hold in board.holds:
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert len(piece.shape.commands) >= 6
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert any(_points(command) for command in piece.shape.commands)

    for family in range(1, 12):
        left = holds[f"hold-{family:02d}-left"].geometry[0]
        right = holds[f"hold-{family:02d}-right"].geometry[0]
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
            left_points = _points(left_command)
            right_points = _points(right_command)
            assert len(right_points) == len(left_points)
            for (left_x, left_y), (right_x, right_y) in zip(
                left_points, right_points, strict=True
            ):
                assert right_x == pytest.approx(1 - left_x)
                assert right_y == pytest.approx(left_y)

    assert all(hold.grip_type is None for hold in board.holds)
    assert all(hold.finger_capacity is None for hold in board.holds)
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)
