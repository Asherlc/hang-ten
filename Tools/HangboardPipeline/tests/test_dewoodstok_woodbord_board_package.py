from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

import pytest
from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "dewoodstok-woodbord"
PRESENTATION_SIZE = (1774, 887)
EXPECTED_PIXEL_FRAMES = {
    "top-rim": (64, 232, 1646, 48),
    "front-upper-1": (112, 287, 253, 72),
    "front-upper-2": (419, 286, 118, 73),
    "front-upper-3": (594, 287, 262, 71),
    "front-upper-4": (918, 287, 262, 71),
    "front-upper-5": (1237, 286, 118, 73),
    "front-upper-6": (1409, 287, 253, 72),
    "front-middle-1": (112, 410, 253, 71),
    "front-middle-2": (419, 410, 248, 71),
    "front-middle-3": (1107, 410, 248, 71),
    "front-middle-4": (1409, 410, 253, 71),
    "front-lower-1": (112, 532, 253, 72),
    "front-lower-2": (419, 531, 118, 74),
    "front-lower-3": (594, 532, 263, 72),
    "front-lower-4": (917, 532, 263, 72),
    "front-lower-5": (1237, 531, 118, 74),
    "front-lower-6": (1409, 532, 253, 72),
}
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
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold.id: hold for hold in board.holds}

    with Image.open(PACKAGE_ROOT / "assets" / "primary.png") as image:
        assert image.size == PRESENTATION_SIZE
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board.id == "dewoodstok-woodbord"
    assert board.manufacturer == "deWoodstok"
    assert board.name == "Woodbord"
    assert board.facts["subtitle"] == "FSC-certified bamboo hangboard."
    assert board.facts["productURL"] == "https://www.dewoodstok.nl/product/hangboard-woodbord/"
    assert board.facts["dimensions"] == "590 × 148 × 40 mm"
    assert math.isclose(board.facts["aspectRatio"], 590 / 148, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in holds.values()) == {"pocket": 16, "sloper": 1}
    assert holds["top-rim"].kind == "sloper"
    assert all(holds[hold_id].kind == "pocket" for hold_id in EXPECTED_HOLDS[1:])
    assert all(hold.size_millimeters is None for hold in holds.values())
    assert all(hold.depth_range_millimeters is None for hold in holds.values())
    assert all(hold.grip_type is None for hold in holds.values())
    assert all(hold.features is None for hold in holds.values())

    for hold in holds.values():
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert any(command.command == "curve" for command in piece.shape.commands)
        assert len(piece.shape.commands) >= 6
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0
        expected_x, expected_y, expected_width, expected_height = EXPECTED_PIXEL_FRAMES[
            hold.id
        ]
        assert math.isclose(
            piece.frame.x * PRESENTATION_SIZE[0], expected_x, abs_tol=0.002
        )
        assert math.isclose(
            piece.frame.y * PRESENTATION_SIZE[1], expected_y, abs_tol=0.002
        )
        assert math.isclose(
            piece.frame.width * PRESENTATION_SIZE[0], expected_width, abs_tol=0.002
        )
        assert math.isclose(
            piece.frame.height * PRESENTATION_SIZE[1], expected_height, abs_tol=0.002
        )

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

    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    for forbidden in (
        "sizeMillimeters",
        "depthRangeMillimeters",
        "gripType",
        "features",
        "cueStyle",
        "shortLabel",
        "detail",
        "semantics",
        "evidence",
        "claims",
        "instructions",
    ):
        assert forbidden not in raw_document
