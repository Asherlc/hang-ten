from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "yy-verticalboard-evo"
EXPECTED_HOLDS = (
    ("jug-left", "jug"),
    ("jug-right", "jug"),
    ("sloper-43-left", "sloper"),
    ("sloper-43-right", "sloper"),
    ("sloper-38-left", "sloper"),
    ("sloper-38-right", "sloper"),
    ("sloper-30-center", "sloper"),
    ("edge-25-left", "edge"),
    ("edge-25-right", "edge"),
    ("edge-20-left", "edge"),
    ("edge-20-right", "edge"),
    ("edge-18-left", "edge"),
    ("edge-18-right", "edge"),
    ("edge-40-center", "edge"),
    ("edge-inclined-30-left", "edge"),
    ("edge-inclined-30-right", "edge"),
    ("pocket-20-two-left", "pocket"),
    ("pocket-20-two-right", "pocket"),
    ("pocket-inclined-25-two-left", "pocket"),
    ("pocket-inclined-25-two-right", "pocket"),
    ("pocket-mono-one-phalanx-left", "pocket"),
    ("pocket-mono-one-phalanx-right", "pocket"),
    ("pocket-mono-two-phalanges-left", "pocket"),
    ("pocket-mono-two-phalanges-right", "pocket"),
    ("handle-center", "jug"),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-43-left", "sloper-43-right"),
    ("sloper-38-left", "sloper-38-right"),
    ("edge-25-left", "edge-25-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-18-left", "edge-18-right"),
    ("edge-inclined-30-left", "edge-inclined-30-right"),
    ("pocket-20-two-left", "pocket-20-two-right"),
    ("pocket-inclined-25-two-left", "pocket-inclined-25-two-right"),
    ("pocket-mono-one-phalanx-left", "pocket-mono-one-phalanx-right"),
    ("pocket-mono-two-phalanges-left", "pocket-mono-two-phalanges-right"),
)
DEPTHS = {
    "edge-25-left": 25,
    "edge-25-right": 25,
    "edge-20-left": 20,
    "edge-20-right": 20,
    "edge-18-left": 18,
    "edge-18-right": 18,
    "edge-40-center": 40,
    "edge-inclined-30-left": 30,
    "edge-inclined-30-right": 30,
    "pocket-20-two-left": 20,
    "pocket-20-two-right": 20,
    "pocket-inclined-25-two-left": 25,
    "pocket-inclined-25-two-right": 25,
}
FINGER_CAPACITIES = {
    "pocket-20-two-left": 2,
    "pocket-20-two-right": 2,
    "pocket-inclined-25-two-left": 2,
    "pocket-inclined-25-two-right": 2,
    "pocket-mono-one-phalanx-left": 1,
    "pocket-mono-one-phalanx-right": 1,
    "pocket-mono-two-phalanges-left": 1,
    "pocket-mono-two-phalanges-right": 1,
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_exact_global_mirror(left: object, right: object) -> None:
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


def _recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_recursive_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_recursive_keys(child) for child in value))
    return set()


def test_yy_verticalboard_evo_preserves_audited_inventory_and_geometry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board.id == "yy.verticalboard-evo"
    assert board.manufacturer == "YY Vertical"
    assert board.name == "VerticalBoard Evo"
    assert board.facts["dimensions"] == "65 × 14 × 5.5 cm"
    assert math.isclose(board.facts["aspectRatio"], 65 / 14, abs_tol=1e-12)
    assert board.facts["productURL"] == (
        "https://www.yyvertical.com/en/collections/entrainement/products/"
        "verticalboard-evo"
    )
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple((hold.id, hold.kind) for hold in board.holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "jug": 3,
        "edge": 9,
        "pocket": 8,
        "sloper": 5,
    }

    assert {hold_id: holds[hold_id].size_millimeters for hold_id in DEPTHS} == DEPTHS
    assert {
        hold_id: holds[hold_id].finger_capacity for hold_id in FINGER_CAPACITIES
    } == FINGER_CAPACITIES
    assert all(
        hold.size_millimeters is None
        for hold in board.holds
        if hold.id not in DEPTHS
    )
    assert all(
        hold.finger_capacity is None
        for hold in board.holds
        if hold.id not in FINGER_CAPACITIES
    )
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.grip_type is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)

    assert sum(len(hold.geometry) for hold in board.holds) == 25
    for hold in board.holds:
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        commands = [command.command for command in piece.shape.commands]
        assert commands[0] == "move"
        assert commands[-1] == "close"
        assert len(commands) >= 6
        assert set(commands) == {"move", "curve", "close"}
        assert all(
            0 <= coordinate <= 1
            for command in piece.shape.commands
            for point in _points(command)
            for coordinate in point
        )
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_exact_global_mirror(
            holds[left_id].geometry[0], holds[right_id].geometry[0]
        )

    for center_id in ("sloper-30-center", "edge-40-center", "handle-center"):
        frame = holds[center_id].geometry[0].frame
        assert frame.x + frame.width / 2 == pytest.approx(0.5, abs=1e-12)
    assert holds["sloper-30-center"].frame.y < holds["edge-40-center"].frame.y
    assert holds["edge-40-center"].frame.y < holds["handle-center"].frame.y
    assert holds["handle-center"].frame.width > holds["edge-40-center"].frame.width

    # The source board occupies approximately x=.035...965 and y=.284...684
    # on its native canvas; every selectable contact stays inside that body.
    assert all(hold.frame.x >= 0.03 for hold in board.holds)
    assert all(hold.frame.x + hold.frame.width <= 0.97 for hold in board.holds)
    assert all(hold.frame.y >= 0.28 for hold in board.holds)
    assert all(hold.frame.y + hold.frame.height <= 0.69 for hold in board.holds)

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text("utf-8"))
    forbidden = {
        "artwork",
        "catalog",
        "claims",
        "cueStyle",
        "evidence",
        "semantics",
    }
    assert forbidden.isdisjoint(_recursive_keys(raw_document))
