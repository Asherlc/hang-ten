from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

from hangboard_packages.board_catalog import load_board_package
from _board_package_helpers import presentation_frame


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "escape-beta-22"
EXPECTED_HOLDS = (
    *(
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
        )
        for side in ("left", "right")
    ),
    ("hold-09-center", "sloper"),
    ("hold-10-center", "sloper"),
    ("hold-11-center", "sloper"),
)
EXPECTED_SIZES = {
    **{
        f"hold-{family:02d}-{side}": size
        for family, size in (
            (1, None),
            (2, None),
            (3, 38),
            (4, 29),
            (5, 12),
            (6, 38),
            (7, 29),
            (8, 12),
        )
        for side in ("left", "right")
    },
    "hold-09-center": 50,
    "hold-10-center": 31,
    "hold-11-center": None,
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_mirrored_pieces(
    left: object,
    right: object,
    presentation_size: tuple[int, int],
) -> float:
    left_pixel_x, left_pixel_y, left_pixel_width, left_pixel_height = presentation_frame(
        left.frame, presentation_size
    )
    right_pixel_x, right_pixel_y, right_pixel_width, right_pixel_height = presentation_frame(
        right.frame, presentation_size
    )
    assert right_pixel_y == pytest.approx(left_pixel_y, abs=1e-6)
    assert right_pixel_width == pytest.approx(left_pixel_width, abs=1e-6)
    assert right_pixel_height == pytest.approx(left_pixel_height, abs=1e-6)
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
    return (left_pixel_x + left_pixel_width + right_pixel_x) / 2


def test_escape_beta_22_audited_inventory_geometry_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}
    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as image:
        presentation_size = image.size

    assert board.id == "escape-beta-22"
    assert tuple((hold.id, hold.kind) for hold in board.holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "pinch": 4,
        "jug": 4,
        "edge": 8,
        "sloper": 3,
    }
    assert sum(len(hold.geometry) for hold in board.holds) == 22

    for hold in board.holds:
        expected_piece_count = 2 if hold.id.endswith("-center") else 1
        assert len(hold.geometry) == expected_piece_count
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert len(piece.shape.commands) >= 6
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert any(_points(command) for command in piece.shape.commands)

    symmetry_axis_x: float | None = None
    for family in range(1, 9):
        left = holds[f"hold-{family:02d}-left"].geometry[0]
        right = holds[f"hold-{family:02d}-right"].geometry[0]
        pair_axis_x = _assert_mirrored_pieces(left, right, presentation_size)
        if symmetry_axis_x is None:
            symmetry_axis_x = pair_axis_x
        else:
            assert pair_axis_x == pytest.approx(symmetry_axis_x, abs=1e-6)

    assert symmetry_axis_x is not None
    for family in range(9, 12):
        left, right = holds[f"hold-{family:02d}-center"].geometry
        pair_axis_x = _assert_mirrored_pieces(left, right, presentation_size)
        assert pair_axis_x == pytest.approx(symmetry_axis_x, abs=1e-6)

    assert 0 < symmetry_axis_x < presentation_size[0]

    for hold in board.holds:
        assert hold.size_millimeters == EXPECTED_SIZES[hold.id]
        assert hold.grip_type is None
        assert hold.finger_capacity is None
        assert hold.features is None
        assert hold.depth_range_millimeters is None
