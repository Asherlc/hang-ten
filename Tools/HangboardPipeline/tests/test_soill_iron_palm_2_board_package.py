from __future__ import annotations

import math
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "soill-iron-palm-2"
EXPECTED_HOLDS = (
    ("sloper-left", "sloper", None, 1),
    ("sloper-right", "sloper", None, 1),
    ("pinch-left", "pinch", None, 2),
    ("pinch-right", "pinch", None, 2),
    ("top-jug-rail", "jug", None, 1),
    ("rounded-edge-40", "edge", 40, 1),
    ("flat-edge-25", "edge", 25, 1),
    ("flat-edge-15", "edge", 15, 1),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_soill_iron_palm_2_preserves_audited_contacts_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "soill.iron-palm-2"
    assert board.manufacturer == "So iLL"
    assert board.name == "Iron Palm 2.0"
    assert board.facts["dimensions"] == "27 × 11.5 × 4 in"
    assert math.isclose(board.facts["aspectRatio"], 27 / 11.5, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters, len(hold.geometry))
        for hold in board.holds
    ) == EXPECTED_HOLDS

    for hold in board.holds:
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert any(command.command == "curve" for command in piece.shape.commands)
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in (
        ("sloper-left", "sloper-right"),
        ("pinch-left", "pinch-right"),
    ):
        for left, right in zip(
            holds[left_id].geometry, holds[right_id].geometry, strict=True
        ):
            assert math.isclose(
                right.frame.x,
                1 - left.frame.x - left.frame.width,
                abs_tol=1e-12,
            )
            assert math.isclose(right.frame.y, left.frame.y, abs_tol=1e-12)
            assert math.isclose(right.frame.width, left.frame.width, abs_tol=1e-12)
            assert math.isclose(right.frame.height, left.frame.height, abs_tol=1e-12)
            for left_command, right_command in zip(
                left.shape.commands, right.shape.commands, strict=True
            ):
                assert left_command.command == right_command.command
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                    assert math.isclose(right_y, left_y, abs_tol=1e-12)

    assert all(len(holds[hold_id].geometry) == 1 for hold_id in (
        "top-jug-rail",
        "rounded-edge-40",
        "flat-edge-25",
        "flat-edge-15",
    ))
    assert holds["top-jug-rail"].geometry[0].treatment == {
        "type": "shelf",
        "rimInsetFraction": 0.12,
    }
    assert holds["sloper-left"].grip_type == "sloper"
    assert holds["sloper-right"].grip_type == "sloper"
    assert all(hold.finger_capacity is None for hold in board.holds)
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)
