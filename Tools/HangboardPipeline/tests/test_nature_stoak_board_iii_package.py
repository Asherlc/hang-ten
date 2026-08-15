from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "nature-stoak-board-iii"
EXPECTED_HOLDS = (
    ("comfortable-jug-left", "jug", None),
    ("comfortable-jug-right", "jug", None),
    ("gradient-edge-10-25-left", "edge", None),
    ("gradient-edge-10-25-right", "edge", None),
    ("granite-edge-20-left", "edge", 20),
    ("granite-edge-20-right", "edge", 20),
    ("wood-edge-30-left", "edge", 30),
    ("wood-edge-30-right", "edge", 30),
    ("center-open-hand-55", "jug", 55),
    ("center-edge-22", "edge", 22),
    ("center-granite-edge-30", "edge", 30),
)
MIRRORED_PAIRS = (
    ("comfortable-jug-left", "comfortable-jug-right"),
    ("gradient-edge-10-25-left", "gradient-edge-10-25-right"),
    ("granite-edge-20-left", "granite-edge-20-right"),
    ("wood-edge-30-left", "wood-edge-30-right"),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_stoak_board_iii_preserves_official_inventory_and_exact_geometry() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board.id == "nature-climbing.stoak-board-iii"
    assert board.manufacturer == "Nature Climbing"
    assert board.name == "Stoak Board III"
    assert board.facts["dimensions"] == "57 × 12 × 5.5 cm"
    assert math.isclose(board.facts["aspectRatio"], 57 / 12, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {"edge": 8, "jug": 3}

    for hold in board.holds:
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert any(command.command == "curve" for command in piece.shape.commands)
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
        assert math.isclose(
            right.frame.x, 1 - left.frame.x - left.frame.width, abs_tol=1e-12
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

    for hold_id in (
        "gradient-edge-10-25-left",
        "gradient-edge-10-25-right",
    ):
        depth_range = holds[hold_id].depth_range_millimeters
        assert depth_range is not None
        assert (depth_range.lower_bound, depth_range.upper_bound) == (10, 25)
    assert holds["center-open-hand-55"].grip_type == "openHand"
    assert all(hold.finger_capacity is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)

    for hold_id in (
        "center-open-hand-55",
        "center-edge-22",
        "center-granite-edge-30",
    ):
        frame = holds[hold_id].geometry[0].frame
        assert math.isclose(frame.x, 1 - frame.x - frame.width, abs_tol=1e-12)


def test_stoak_board_iii_excludes_nonphysical_package_data() -> None:
    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")

    for forbidden in (
        "cueStyle",
        "semantics",
        "evidence",
        "claims",
        "features",
        "fingerCapacity",
        "shortLabel",
        "detail",
    ):
        assert forbidden not in raw_document
