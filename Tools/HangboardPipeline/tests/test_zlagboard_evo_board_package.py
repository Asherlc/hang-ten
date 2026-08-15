from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "zlagboard-evo"
PRIMARY = PACKAGE_ROOT / "assets" / "primary.png"
EXPECTED_HOLDS = (
    ("jug-top-left", "jug", None),
    ("sloper-32-left", "sloper", None),
    ("sloper-20-left", "sloper", None),
    ("jug-sloper-center", "jug", None),
    ("sloper-20-right", "sloper", None),
    ("sloper-32-right", "sloper", None),
    ("jug-top-right", "jug", None),
    ("edge-upper-30-left", "edge", 30),
    ("sloper-upper-30-left", "sloper", 30),
    ("sloper-upper-25-left", "sloper", 25),
    ("edge-upper-35-center", "edge", 35),
    ("sloper-upper-25-right", "sloper", 25),
    ("sloper-upper-30-right", "sloper", 30),
    ("edge-upper-30-right", "edge", 30),
    ("edge-lower-20-left", "edge", 20),
    ("sloper-lower-25-left", "sloper", 25),
    ("pocket-lower-30-left", "pocket", 30),
    ("sloper-lower-30-center", "sloper", 30),
    ("pocket-lower-30-right", "pocket", 30),
    ("sloper-lower-25-right", "sloper", 25),
    ("edge-lower-20-right", "edge", 20),
)
MIRRORED_PAIRS = (
    ("jug-top-left", "jug-top-right"),
    ("sloper-32-left", "sloper-32-right"),
    ("sloper-20-left", "sloper-20-right"),
    ("edge-upper-30-left", "edge-upper-30-right"),
    ("sloper-upper-30-left", "sloper-upper-30-right"),
    ("sloper-upper-25-left", "sloper-upper-25-right"),
    ("edge-lower-20-left", "edge-lower-20-right"),
    ("sloper-lower-25-left", "sloper-lower-25-right"),
    ("pocket-lower-30-left", "pocket-lower-30-right"),
)


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


def _frame_overlap(first: object, second: object) -> float:
    width = max(
        0.0,
        min(first.x + first.width, second.x + second.width)
        - max(first.x, second.x),
    )
    height = max(
        0.0,
        min(first.y + first.height, second.y + second.height)
        - max(first.y, second.y),
    )
    return width * height


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(child) for child in value))
    return set()


def test_zlagboard_evo_preserves_audited_inventory_geometry_and_asset() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "zlagboard.evo"
    assert board.manufacturer == "Zlagboard"
    assert board.name == "Zlagboard Evo"
    assert board.facts["productURL"] == "https://www.zlagboard.com/hangboards"
    assert board.facts["dimensions"] == "8 × 23 × 70.5 cm"
    assert math.isclose(board.facts["aspectRatio"], 70.5 / 8, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }

    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert holds["jug-sloper-center"].name == "Center sloper JUG"
    assert Counter(hold.kind for hold in board.holds) == {
        "jug": 3,
        "sloper": 11,
        "edge": 5,
        "pocket": 2,
    }
    assert len(board.holds) == 21
    assert sum(len(hold.geometry) for hold in board.holds) == 21

    pieces = []
    for hold in board.holds:
        assert len(hold.geometry) == 1
        assert hold.finger_capacity is None
        assert hold.grip_type is None
        assert hold.features is None
        assert hold.depth_range_millimeters is None
        piece = hold.geometry[0]
        pieces.append(piece)
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert sum(
            command.command == "curve" for command in piece.shape.commands
        ) >= 4
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    assert len({(piece.frame, piece.shape) for piece in pieces}) == 21
    for index, first in enumerate(pieces):
        for second in pieces[index + 1 :]:
            assert _frame_overlap(first.frame, second.frame) == pytest.approx(
                0.0, abs=1e-12
            )

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_exact_global_mirror(
            holds[left_id].geometry[0], holds[right_id].geometry[0]
        )
    for center_id in ("edge-upper-35-center", "sloper-lower-30-center"):
        center = holds[center_id].geometry[0].frame
        assert center.x == pytest.approx(1 - center.x - center.width, abs=1e-12)

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {
        "cueStyle",
        "shortLabel",
        "semantics",
        "evidence",
        "claims",
        "ui",
        "instructions",
        "fingerCapacity",
        "gripType",
        "features",
        "depthRangeMillimeters",
    }
    assert forbidden.isdisjoint(_keys(raw))

    assert sha256(PRIMARY.read_bytes()).hexdigest() == (
        "a7bb1306f6f234637d6dc480b21ee1a41af8ef3fe3dc0e092160f6eae4054787"
    )
    with Image.open(PRIMARY) as image:
        assert image.size == (2081, 755)
        assert image.mode == "RGB"
