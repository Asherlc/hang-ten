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
    "hold-09-center": None,
    "hold-11-center": None,
}
CENTER_HOLDS = ("hold-09-center", "hold-11-center")


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _frame_seam_x(left: object, right: object) -> float:
    assert left.frame.x + left.frame.width <= right.frame.x
    return left.frame.x + left.frame.width


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
        "sloper": 2,
    }
    assert sum(len(hold.geometry) for hold in board.holds) == 20

    for hold in board.holds:
        expected_piece_count = 2 if hold.id.endswith("-center") else 1
        assert len(hold.geometry) == expected_piece_count
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert len(piece.shape.commands) >= 5
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert any(_points(command) for command in piece.shape.commands)

    for family in range(1, 9):
        left = holds[f"hold-{family:02d}-left"]
        right = holds[f"hold-{family:02d}-right"]
        assert left.kind == right.kind
        assert left.size_millimeters == right.size_millimeters
        left_piece = left.geometry[0]
        right_piece = right.geometry[0]
        assert left_piece.frame.x < right_piece.frame.x
        left_x, _, left_width, _ = presentation_frame(left.frame, presentation_size)
        right_x, _, _, _ = presentation_frame(right.frame, presentation_size)
        assert left_x + left_width <= right_x

    seam_x: float | None = None
    for hold_id in CENTER_HOLDS:
        left, right = holds[hold_id].geometry
        pair_seam_x = _frame_seam_x(left, right)
        if seam_x is None:
            seam_x = pair_seam_x
        else:
            assert pair_seam_x == pytest.approx(seam_x, abs=1e-9)

    assert seam_x is not None
    assert 0 < seam_x < 1

    for hold in board.holds:
        assert hold.size_millimeters == EXPECTED_SIZES[hold.id]
        assert hold.grip_type is None
        assert hold.finger_capacity is None
        assert hold.features is None
        assert hold.depth_range_millimeters is None
