from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-climbers-edge"
EXPECTED_HOLDS = (
    "jug-left",
    "sloper-flat-left",
    "sloper-round-center",
    "sloper-flat-right",
    "jug-right",
    "edge-20-left",
    "edge-15-left",
    "edge-10-center",
    "edge-15-right",
    "edge-20-right",
    "edge-17-5-left",
    "edge-12-5-left",
    "edge-7-5-center",
    "edge-12-5-right",
    "edge-17-5-right",
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-flat-left", "sloper-flat-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-15-left", "edge-15-right"),
    ("edge-17-5-left", "edge-17-5-right"),
    ("edge-12-5-left", "edge-12-5-right"),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_metolius_climbers_edge_audited_inventory_and_exact_geometry() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board.id == "metolius.climbers-edge"
    assert board.manufacturer == "Metolius"
    assert board.name == "Climbers Edge Board"
    assert board.facts["dimensions"] == "600 × 160 mm"
    assert board.facts["aspectRatio"] == 3.75
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in holds.values()) == {"edge": 10, "sloper": 3, "jug": 2}

    assert holds["jug-left"].features == ("jug",)
    assert holds["jug-right"].features == ("jug",)
    assert holds["sloper-round-center"].features == ("roundSloper",)
    assert all(holds[hold_id].grip_type == "sloper" for hold_id in (
        "sloper-flat-left", "sloper-round-center", "sloper-flat-right"
    ))
    assert {
        hold_id: holds[hold_id].size_millimeters
        for hold_id in ("edge-20-left", "edge-20-right", "edge-15-left", "edge-15-right", "edge-10-center")
    } == {
        "edge-20-left": 20,
        "edge-20-right": 20,
        "edge-15-left": 15,
        "edge-15-right": 15,
        "edge-10-center": 10,
    }
    assert all(holds[hold_id].size_millimeters is None for hold_id in (
        "edge-17-5-left", "edge-17-5-right", "edge-12-5-left",
        "edge-12-5-right", "edge-7-5-center",
    ))
    assert all(hold.finger_capacity is None for hold in holds.values())
    assert all(hold.depth_range_millimeters is None for hold in holds.values())

    for hold in holds.values():
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
        assert math.isclose(right.frame.x, 1 - left.frame.x - left.frame.width, abs_tol=1e-12)
        assert right.frame.y == left.frame.y
        assert right.frame.width == left.frame.width
        assert right.frame.height == left.frame.height
        for left_command, right_command in zip(
            left.shape.commands, right.shape.commands, strict=True
        ):
            assert left_command.command == right_command.command
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    top_ids = (
        "jug-left", "sloper-flat-left", "sloper-round-center",
        "sloper-flat-right", "jug-right",
    )
    for left_id, right_id in zip(top_ids, top_ids[1:]):
        assert math.isclose(
            holds[left_id].frame.x + holds[left_id].frame.width,
            holds[right_id].frame.x,
            abs_tol=1e-12,
        )

    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    for forbidden in ("cueStyle", "evidence", "claims", "shortLabel", "detail"):
        assert forbidden not in raw_document
