from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "soill-iron-palm-2"
PRESENTATION_SIZE = (1536, 1024)
EXPECTED_HOLDS = (
    ("sloper-left", "Left big sloper", "sloper", None, 1),
    ("sloper-right", "Right big sloper", "sloper", None, 1),
    ("pinch-left", "Left 3 in pinch", "pinch", None, 2),
    ("pinch-right", "Right 3 in pinch", "pinch", None, 2),
    ("top-jug-rail", "Top incut jug rail", "jug", None, 1),
    ("rounded-edge-40", "40 mm rounded edge", "edge", 40, 1),
    ("flat-edge-35", "35 mm flat edge", "edge", 35, 1),
    ("flat-edge-15", "15 mm flat edge", "edge", 15, 1),
)
EXPECTED_PIXEL_FRAMES = {
    "sloper-left": ((84, 218, 385, 363),),
    "sloper-right": ((1067, 218, 385, 363),),
    "pinch-left": ((42, 529, 231, 289), (144, 710, 139, 147)),
    "pinch-right": ((1263, 529, 231, 289), (1253, 710, 139, 147)),
    "top-jug-rail": ((434, 381, 668, 27),),
    "rounded-edge-40": ((432, 452, 672, 48),),
    "flat-edge-35": ((368, 555, 800, 46),),
    "flat-edge-15": ((321, 665, 894, 73),),
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_soill_iron_palm_2_preserves_audited_contacts_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board.id == "soill.iron-palm-2"
    assert board.manufacturer == "So iLL"
    assert board.name == "Iron Palm 2.0"
    assert board.facts["dimensions"] == "27 × 11.5 × 4 in"
    assert board.presentation_asset_path == "assets/primary.png"
    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as image:
        assert image.size == PRESENTATION_SIZE
        image_aspect_ratio = image.width / image.height
    assert math.isclose(
        board.facts["aspectRatio"],
        image_aspect_ratio,
        rel_tol=0.0,
        abs_tol=1e-12,
    )

    assert len(board.holds) == 8
    assert sum(len(hold.geometry) for hold in board.holds) == 10
    assert Counter(hold.kind for hold in board.holds) == Counter(
        {"sloper": 2, "pinch": 2, "jug": 1, "edge": 3}
    )
    assert tuple(
        (hold.id, hold.name, hold.kind, hold.size_millimeters, len(hold.geometry))
        for hold in board.holds
    ) == EXPECTED_HOLDS

    for hold in board.holds:
        for piece, expected_frame in zip(
            hold.geometry, EXPECTED_PIXEL_FRAMES[hold.id], strict=True
        ):
            assert piece.shape.type == "path"
            commands = piece.shape.commands
            assert commands[0].command == "move"
            assert commands[-1].command == "close"
            assert commands[1:-1]
            assert all(command.command == "curve" for command in commands[1:-1])
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0
            for actual, expected in zip(
                (
                    piece.frame.x * PRESENTATION_SIZE[0],
                    piece.frame.y * PRESENTATION_SIZE[1],
                    piece.frame.width * PRESENTATION_SIZE[0],
                    piece.frame.height * PRESENTATION_SIZE[1],
                ),
                expected_frame,
                strict=True,
            ):
                assert math.isclose(actual, expected, abs_tol=1e-7)

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

    assert len(holds["pinch-left"].geometry) == 2
    assert len(holds["pinch-right"].geometry) == 2
    assert all(len(hold.geometry) == 1 for hold in board.holds if hold.kind != "pinch")
    assert holds["top-jug-rail"].geometry[0].treatment == {
        "type": "shelf",
        "rimInsetFraction": 0.12,
    }
    assert all(
        piece.treatment == {"type": "surface"}
        for hold in board.holds
        if hold.kind != "jug"
        for piece in hold.geometry
    )
    assert holds["sloper-left"].grip_type == "sloper"
    assert holds["sloper-right"].grip_type == "sloper"
    assert all(hold.finger_capacity is None for hold in board.holds)
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)
