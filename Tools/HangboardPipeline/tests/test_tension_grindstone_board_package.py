from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

import pytest
from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "tension-grindstone"
EXPECTED_HOLDS = (
    ("top-jug", "jug", None, 3),
    ("edge-10-left", "edge", 10, 1),
    ("edge-10-right", "edge", 10, 1),
    ("edge-8-left", "edge", 8, 1),
    ("edge-8-right", "edge", 8, 1),
    ("edge-30-left", "edge", 30, 1),
    ("edge-30-right", "edge", 30, 1),
    ("edge-25-left", "edge", 25, 1),
    ("edge-25-right", "edge", 25, 1),
    ("center-edge-50", "edge", 50, 1),
    ("edge-20-left", "edge", 20, 1),
    ("edge-20-right", "edge", 20, 1),
    ("edge-15-left", "edge", 15, 1),
    ("edge-15-right", "edge", 15, 1),
)
PRESENTATION_SIZE = (1672, 941)
EXPECTED_PIXEL_FRAMES = {
    ("top-jug", 0): (31.768, 253.129, 745.712, 26.348),
    ("top-jug", 1): (894.52, 253.129, 745.712, 26.348),
    ("top-jug", 2): (760.76, 265.362, 150.48, 30.112),
    ("edge-10-left", 0): (87.78, 290.769, 278.388, 60.224),
    ("edge-10-right", 0): (1045.0, 290.769, 260.832, 60.224),
    ("edge-8-left", 0): (366.168, 290.769, 260.832, 60.224),
    ("edge-8-right", 0): (1305.832, 290.769, 278.388, 60.224),
    ("edge-30-left", 0): (90.288, 430.978, 299.288, 77.162),
    ("edge-30-right", 0): (1026.608, 430.978, 255.816, 77.162),
    ("edge-25-left", 0): (389.576, 430.978, 255.816, 77.162),
    ("edge-25-right", 0): (1282.424, 430.978, 299.288, 77.162),
    ("center-edge-50", 0): (703.912, 497.789, 264.176, 22.584),
    ("edge-20-left", 0): (112.024, 572.128, 282.568, 79.044),
    ("edge-20-right", 0): (1024.936, 572.128, 252.472, 79.044),
    ("edge-15-left", 0): (394.592, 572.128, 252.472, 79.044),
    ("edge-15-right", 0): (1277.408, 572.128, 282.568, 79.044),
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_piece_is_exact_global_mirror(left: object, right: object) -> None:
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


def test_tension_grindstone_preserves_audited_asymmetric_depth_zones() -> None:
    with Image.open(PACKAGE_ROOT / "assets" / "primary.png") as presentation:
        presentation_size = presentation.size

    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {entry.name for entry in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {entry.name for entry in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert presentation_size == PRESENTATION_SIZE
    assert board.id == "tension.grindstone"
    assert board.manufacturer == "Tension Climbing"
    assert board.name == "Grindstone"
    assert board.facts["dimensions"] == "22 × 6 × 2.75 in"
    assert math.isclose(board.facts["aspectRatio"], 22 / 6, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters, len(hold.geometry))
        for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == Counter({"edge": 13, "jug": 1})
    assert sum(len(hold.geometry) for hold in board.holds) == 16

    visited_frame_keys = set()
    for hold in board.holds:
        for piece_index, piece in enumerate(hold.geometry):
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert all(
                command.command in {"move", "curve", "close"}
                for command in piece.shape.commands
            )
            assert sum(
                command.command == "curve" for command in piece.shape.commands
            ) >= 4
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0

            frame_key = (hold.id, piece_index)
            visited_frame_keys.add(frame_key)
            actual_pixel_frame = (
                piece.frame.x * presentation_size[0],
                piece.frame.y * presentation_size[1],
                piece.frame.width * presentation_size[0],
                piece.frame.height * presentation_size[1],
            )
            for actual, expected in zip(
                actual_pixel_frame, EXPECTED_PIXEL_FRAMES[frame_key], strict=True
            ):
                assert math.isclose(actual, expected, abs_tol=1e-6)
    assert visited_frame_keys == set(EXPECTED_PIXEL_FRAMES)

    _assert_piece_is_exact_global_mirror(
        holds["top-jug"].geometry[0], holds["top-jug"].geometry[1]
    )
    assert holds["top-jug"].geometry[2].frame.x == pytest.approx(
        1
        - holds["top-jug"].geometry[2].frame.x
        - holds["top-jug"].geometry[2].frame.width,
        abs=1e-12,
    )

    # The routed cavities are physically mirrored, but the depth labels are
    # intentionally asymmetric. A same-ID mirror would attach the wrong depth.
    for left_id, right_id in (
        ("edge-10-left", "edge-8-right"),
        ("edge-8-left", "edge-10-right"),
        ("edge-30-left", "edge-25-right"),
        ("edge-25-left", "edge-30-right"),
        ("edge-20-left", "edge-15-right"),
        ("edge-15-left", "edge-20-right"),
    ):
        _assert_piece_is_exact_global_mirror(
            holds[left_id].geometry[0], holds[right_id].geometry[0]
        )

    for same_depth_left, same_depth_right in (
        ("edge-10-left", "edge-10-right"),
        ("edge-8-left", "edge-8-right"),
        ("edge-30-left", "edge-30-right"),
        ("edge-25-left", "edge-25-right"),
        ("edge-20-left", "edge-20-right"),
        ("edge-15-left", "edge-15-right"),
    ):
        assert holds[same_depth_left].frame.x < 0.5
        assert holds[same_depth_right].frame.x > 0.5

    for left_id, right_id in (
        ("edge-10-left", "edge-8-left"),
        ("edge-10-right", "edge-8-right"),
        ("edge-30-left", "edge-25-left"),
        ("edge-30-right", "edge-25-right"),
        ("edge-20-left", "edge-15-left"),
        ("edge-20-right", "edge-15-right"),
    ):
        left, right = sorted(
            (holds[left_id].geometry[0], holds[right_id].geometry[0]),
            key=lambda piece: piece.frame.x,
        )
        assert left.frame.x + left.frame.width == pytest.approx(
            right.frame.x, abs=1e-12
        )
        assert left.frame.y == pytest.approx(right.frame.y, abs=1e-12)
        assert left.frame.height == pytest.approx(right.frame.height, abs=1e-12)

    assert all(hold.grip_type is None for hold in board.holds)
    assert all(hold.finger_capacity is None for hold in board.holds)
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)
