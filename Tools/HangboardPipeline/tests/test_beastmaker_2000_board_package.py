from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "beastmaker-2000"
EXPECTED_HOLDS = (
    *(f"top-sloper-{index}" for index in range(1, 6)),
    *(f"front-upper-{index}" for index in range(1, 3)),
    *(f"front-middle-{index}" for index in range(1, 10)),
    *(f"front-lower-{index}" for index in range(1, 10)),
)
EXPECTED_KINDS = {
    **{f"top-sloper-{index}": "sloper" for index in range(1, 6)},
    "front-upper-1": "pocket",
    "front-upper-2": "pocket",
    "front-middle-1": "edge",
    "front-middle-2": "pocket",
    "front-middle-3": "pocket",
    "front-middle-4": "edge",
    "front-middle-5": "jug",
    "front-middle-6": "edge",
    "front-middle-7": "pocket",
    "front-middle-8": "pocket",
    "front-middle-9": "edge",
    "front-lower-1": "edge",
    "front-lower-2": "pocket",
    "front-lower-3": "edge",
    "front-lower-4": "edge",
    "front-lower-5": "edge",
    "front-lower-6": "edge",
    "front-lower-7": "edge",
    "front-lower-8": "pocket",
    "front-lower-9": "edge",
}
MIRRORED_PAIRS = (
    ("top-sloper-1", "top-sloper-5"),
    ("top-sloper-2", "top-sloper-4"),
    ("front-upper-1", "front-upper-2"),
    *((f"front-middle-{left}", f"front-middle-{10 - left}") for left in range(1, 5)),
    *((f"front-lower-{left}", f"front-lower-{10 - left}") for left in range(1, 5)),
)


def test_beastmaker_2000_inventory_paths_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert tuple(holds) == EXPECTED_HOLDS
    assert {hold_id: hold.kind for hold_id, hold in holds.items()} == EXPECTED_KINDS
    assert Counter(hold.kind for hold in holds.values()) == {
        "sloper": 5,
        "edge": 11,
        "pocket": 8,
        "jug": 1,
    }

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
        left = holds[left_id].frame
        right = holds[right_id].frame
        assert right.x == pytest.approx(1 - left.x - left.width, abs=1e-6)
        assert right.y == pytest.approx(left.y, abs=1e-6)
        assert right.width == pytest.approx(left.width, abs=1e-6)
        assert right.height == pytest.approx(left.height, abs=1e-6)
