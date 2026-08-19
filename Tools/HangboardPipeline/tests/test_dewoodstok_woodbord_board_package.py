from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

from hangboard_vectorizer.board_catalog import NormalizedFrame, load_board_package


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


def _presentation_frame(
    frame: NormalizedFrame, size: tuple[int, int]
) -> tuple[float, float, float, float]:
    width, height = size
    return (
        frame.x * width,
        frame.y * height,
        frame.width * width,
        frame.height * height,
    )


def test_dewoodstok_woodbord_inventory_geometry_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}
    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as image:
        presentation_size = image.size

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

    symmetry_axis_x: float | None = None
    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]
        right = holds[right_id]
        left_x, left_y, left_width, left_height = _presentation_frame(
            left.frame, presentation_size
        )
        right_x, right_y, right_width, right_height = _presentation_frame(
            right.frame, presentation_size
        )
        assert right_y == pytest.approx(left_y, abs=1e-6)
        assert right_width == pytest.approx(left_width, abs=1e-6)
        assert right_height == pytest.approx(left_height, abs=1e-6)
        assert right.geometry[0].shape.commands == left.geometry[0].shape.commands
        pair_axis_x = (left_x + left_width + right_x) / 2
        if symmetry_axis_x is None:
            symmetry_axis_x = pair_axis_x
        else:
            assert pair_axis_x == pytest.approx(symmetry_axis_x, abs=1e-6)

    assert symmetry_axis_x is not None
    assert 0 < symmetry_axis_x < presentation_size[0]

    capacities = Counter(hold.finger_capacity for hold in holds.values())
    assert capacities == {4: 12, 2: 4, None: 1}
