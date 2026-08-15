from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "dewoodstok-woodbord"
EXPECTED_HOLDS = (
    "top-rim",
    *(f"front-upper-{index}" for index in range(1, 7)),
    *(f"front-middle-{index}" for index in range(1, 5)),
    *(f"front-lower-{index}" for index in range(1, 7)),
)
MIRRORED_PAIRS = (
    *((f"front-upper-{left}", f"front-upper-{7 - left}") for left in range(1, 4)),
    *((f"front-middle-{left}", f"front-middle-{5 - left}") for left in range(1, 3)),
    *((f"front-lower-{left}", f"front-lower-{7 - left}") for left in range(1, 4)),
)


def test_dewoodstok_woodbord_inventory_geometry_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert tuple(holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in holds.values()) == {"pocket": 16, "sloper": 1}
    assert holds["top-rim"].kind == "sloper"
    assert all(holds[hold_id].kind == "pocket" for hold_id in EXPECTED_HOLDS[1:])

    for hold in holds.values():
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert len(piece.shape.commands) >= 6
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]
        right = holds[right_id]
        assert right.frame.x == pytest.approx(1 - left.frame.x - left.frame.width, abs=1e-6)
        assert right.frame.y == pytest.approx(left.frame.y, abs=1e-6)
        assert right.frame.width == pytest.approx(left.frame.width, abs=1e-6)
        assert right.frame.height == pytest.approx(left.frame.height, abs=1e-6)
        assert right.geometry[0].shape.commands == left.geometry[0].shape.commands

    capacities = Counter(hold.finger_capacity for hold in holds.values())
    assert capacities == {4: 12, 2: 4, None: 1}
