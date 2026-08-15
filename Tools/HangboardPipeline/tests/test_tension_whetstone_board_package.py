from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "tension-whetstone"
PRESENTATION_SIZE = (1536, 1024)
EXPECTED_PIXEL_FRAMES = {
    "top-jug": (32, 344, 1472, 77.08333333333333),
    "pocket-40-two-left": (61, 420.0416666666667, 107, 140.625),
    "pocket-40-two-right": (1368, 420.0416666666667, 107, 140.625),
    "edge-40-left": (226, 453.375, 185, 53.125),
    "edge-40-right": (962, 453.375, 163, 53.125),
    "edge-30-left": (411, 453.375, 163, 53.125),
    "edge-30-right": (1125, 453.375, 185, 53.125),
    "center-edge-40": (632, 494, 272, 100),
    "edge-25-left": (226, 589.8333333333334, 185, 71.875),
    "edge-25-right": (962, 589.8333333333334, 163, 71.875),
    "edge-20-left": (411, 589.8333333333334, 163, 71.875),
    "edge-20-right": (1125, 589.8333333333334, 185, 71.875),
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_tension_whetstone_audited_inventory_and_contact_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    with Image.open(PACKAGE_ROOT / "assets" / "primary.png") as presentation:
        assert presentation.size == PRESENTATION_SIZE

    assert board.id == "tension.whetstone"
    assert board.manufacturer == "Tension Climbing"
    assert board.name == "Whetstone"
    assert board.facts["dimensions"] == "25 × 6 × 2 in"
    assert math.isclose(board.facts["aspectRatio"], 25 / 6, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(holds) == (
        "top-jug",
        "pocket-40-two-left",
        "pocket-40-two-right",
        "edge-40-left",
        "edge-40-right",
        "edge-30-left",
        "edge-30-right",
        "center-edge-40",
        "edge-25-left",
        "edge-25-right",
        "edge-20-left",
        "edge-20-right",
    )
    assert Counter(hold.kind for hold in holds.values()) == {
        "edge": 9,
        "pocket": 2,
        "jug": 1,
    }
    assert tuple(
        (hold_id, holds[hold_id].size_millimeters)
        for hold_id in holds
        if hold_id != "top-jug"
    ) == (
        ("pocket-40-two-left", 40),
        ("pocket-40-two-right", 40),
        ("edge-40-left", 40),
        ("edge-40-right", 40),
        ("edge-30-left", 30),
        ("edge-30-right", 30),
        ("center-edge-40", 40),
        ("edge-25-left", 25),
        ("edge-25-right", 25),
        ("edge-20-left", 20),
        ("edge-20-right", 20),
    )
    assert holds["pocket-40-two-left"].finger_capacity == 2
    assert holds["pocket-40-two-right"].finger_capacity == 2
    assert holds["pocket-40-two-left"].grip_type == "twoFingerPocket"
    assert holds["pocket-40-two-right"].grip_type == "twoFingerPocket"
    assert all(
        holds[hold_id].finger_capacity is None and holds[hold_id].grip_type is None
        for hold_id in holds
        if hold_id not in {"pocket-40-two-left", "pocket-40-two-right"}
    )
    assert all(len(hold.geometry) == 1 for hold in holds.values())

    for hold in holds.values():
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert any(command.command == "curve" for command in piece.shape.commands)
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0
        expected_frame = EXPECTED_PIXEL_FRAMES[hold.id]
        actual_frame = (
            piece.frame.x * PRESENTATION_SIZE[0],
            piece.frame.y * PRESENTATION_SIZE[1],
            piece.frame.width * PRESENTATION_SIZE[0],
            piece.frame.height * PRESENTATION_SIZE[1],
        )
        for actual, expected in zip(actual_frame, expected_frame, strict=True):
            assert math.isclose(actual, expected, abs_tol=1e-8)

    # The asymmetric depth labels are translated across otherwise mirrored zones.
    for left_id, right_id in (
        ("pocket-40-two-left", "pocket-40-two-right"),
        ("edge-40-left", "edge-30-right"),
        ("edge-30-left", "edge-40-right"),
        ("edge-25-left", "edge-20-right"),
        ("edge-20-left", "edge-25-right"),
    ):
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
        assert math.isclose(right.frame.x, 1 - left.frame.x - left.frame.width, abs_tol=1e-12)
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

    top_jug = holds["top-jug"].geometry[0]
    assert math.isclose(
        top_jug.frame.x,
        1 - top_jug.frame.x - top_jug.frame.width,
        abs_tol=1e-12,
    )
    center = holds["center-edge-40"].geometry[0]
    assert math.isclose(center.frame.x, 1 - center.frame.x - center.frame.width, abs_tol=1e-12)

    assert all(hold.depth_range_millimeters is None for hold in holds.values())
    assert all(hold.features is None for hold in holds.values())
