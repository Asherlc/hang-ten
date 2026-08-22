from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

from hangboard_packages.board_catalog import load_board_package
from _board_package_helpers import presentation_frame


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "beastmaker-2000"
EXPECTED_HOLDS = (
    *(f"top-sloper-{index}" for index in range(1, 5)),
    *(f"front-upper-{index}" for index in range(1, 3)),
    *(f"front-middle-{index}" for index in range(1, 10)),
    *(f"front-lower-{index}" for index in range(1, 10)),
    "hold-26",
    "hold-27",
)
EXPECTED_KINDS = {
    **{f"top-sloper-{index}": "sloper" for index in range(1, 5)},
    "front-upper-1": "pocket",
    "front-upper-2": "pocket",
    "front-middle-1": "pocket",
    "front-middle-2": "pocket",
    "front-middle-3": "pocket",
    "front-middle-4": "pocket",
    "front-middle-5": "pocket",
    "front-middle-6": "pocket",
    "front-middle-7": "pocket",
    "front-middle-8": "pocket",
    "front-middle-9": "pocket",
    "front-lower-1": "edge",
    "front-lower-2": "pocket",
    "front-lower-3": "pocket",
    "front-lower-4": "pocket",
    "front-lower-5": "pocket",
    "front-lower-6": "pocket",
    "front-lower-7": "pocket",
    "front-lower-8": "pocket",
    "front-lower-9": "pocket",
    "hold-26": "pocket",
    "hold-27": "pocket",
}
MIRRORED_PAIRS = (
    ("front-upper-1", "front-upper-2"),
    ("front-middle-1", "front-middle-9"),
    ("front-middle-3", "front-middle-7"),
    ("front-middle-4", "front-middle-6"),
    *((f"front-lower-{left}", f"front-lower-{10 - left}") for left in range(1, 5)),
)
EXPECTED_CENTERED_HOLDS = ("front-middle-5", "front-lower-5")


def test_beastmaker_2000_inventory_shapes_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}
    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as image:
        presentation_size = image.size

    assert tuple(holds) == EXPECTED_HOLDS
    assert {hold_id: hold.kind for hold_id, hold in holds.items()} == EXPECTED_KINDS
    assert Counter(hold.kind for hold in holds.values()) == {
        "sloper": 4,
        "edge": 1,
        "pocket": 21,
    }

    rounded_rect_holds = {
        hold.id
        for hold in holds.values()
        if hold.geometry[0].shape.type == "roundedRect"
    }
    assert rounded_rect_holds == set()

    for hold in holds.values():
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert len(piece.shape.commands) >= 5
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1

    symmetry_axis_x: float | None = None
    for left_id, right_id in MIRRORED_PAIRS:
        left_x, left_y, left_width, left_height = presentation_frame(
            holds[left_id].frame, presentation_size
        )
        right_x, right_y, right_width, right_height = presentation_frame(
            holds[right_id].frame, presentation_size
        )
        assert right_y == pytest.approx(left_y, abs=1e-6)
        assert right_width == pytest.approx(left_width, abs=1e-6)
        assert right_height == pytest.approx(left_height, abs=1e-6)
        pair_axis_x = (left_x + left_width + right_x) / 2
        if symmetry_axis_x is None:
            symmetry_axis_x = pair_axis_x
        else:
            assert pair_axis_x == pytest.approx(symmetry_axis_x, abs=1e-6)

    assert symmetry_axis_x is not None
    for hold_id in EXPECTED_CENTERED_HOLDS:
        hold_x, _, hold_width, _ = presentation_frame(holds[hold_id].frame, presentation_size)
        hold_axis_x = hold_x + hold_width / 2
        assert hold_axis_x == pytest.approx(symmetry_axis_x, abs=2e-3)
    assert 0 < symmetry_axis_x < presentation_size[0]
