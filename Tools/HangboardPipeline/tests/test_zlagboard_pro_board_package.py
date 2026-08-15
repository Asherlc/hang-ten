from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "zlagboard-pro"
EXPECTED_PRIMARY_SHA256 = (
    "540ef36d327359b564646fa80080298a3ee07b651f1c7ced66ad11773951f148"
)
EXPECTED_HOLDS = (
    ("top-jug-left", "jug", None),
    ("top-sloper-32-left", "sloper", None),
    ("top-sloper-20-left", "sloper", None),
    ("top-sloper-jug-center", "jug", None),
    ("top-sloper-20-right", "sloper", None),
    ("top-sloper-32-right", "sloper", None),
    ("top-jug-right", "jug", None),
    ("upper-edge-30-left", "edge", 30),
    ("upper-sloper-30-left", "sloper", 30),
    ("upper-sloper-25-left", "sloper", 25),
    ("upper-edge-35-center", "edge", 35),
    ("upper-sloper-25-right", "sloper", 25),
    ("upper-sloper-30-right", "sloper", 30),
    ("upper-edge-30-right", "edge", 30),
    ("middle-edge-20-left", "edge", 20),
    ("middle-sloper-25-left", "sloper", 25),
    ("middle-pocket-30-left", "pocket", 30),
    ("middle-sloper-30-center", "sloper", 30),
    ("middle-pocket-30-right", "pocket", 30),
    ("middle-sloper-25-right", "sloper", 25),
    ("middle-edge-20-right", "edge", 20),
    ("lower-incut-edge-15-left", "edge", 15),
    ("lower-edge-15-left", "edge", 15),
    ("lower-incut-pocket-30-left", "pocket", 30),
    ("lower-incut-edge-10-center", "edge", 10),
    ("lower-incut-pocket-30-right", "pocket", 30),
    ("lower-edge-15-right", "edge", 15),
    ("lower-incut-edge-15-right", "edge", 15),
)
MIRRORED_PAIRS = (
    ("top-jug-left", "top-jug-right"),
    ("top-sloper-32-left", "top-sloper-32-right"),
    ("top-sloper-20-left", "top-sloper-20-right"),
    ("upper-edge-30-left", "upper-edge-30-right"),
    ("upper-sloper-30-left", "upper-sloper-30-right"),
    ("upper-sloper-25-left", "upper-sloper-25-right"),
    ("middle-edge-20-left", "middle-edge-20-right"),
    ("middle-sloper-25-left", "middle-sloper-25-right"),
    ("middle-pocket-30-left", "middle-pocket-30-right"),
    ("lower-incut-edge-15-left", "lower-incut-edge-15-right"),
    ("lower-edge-15-left", "lower-edge-15-right"),
    ("lower-incut-pocket-30-left", "lower-incut-pocket-30-right"),
)
FORBIDDEN_KEYS = {
    "cueStyle",
    "claims",
    "semantics",
    "evidence",
    "artwork",
    "catalog",
    "ui",
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_piece_is_exact_global_mirror(left: object, right: object) -> None:
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


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value))
    return set()


def test_zlagboard_pro_preserves_the_audited_physical_inventory() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board.id == "zlagboard.pro"
    assert board.manufacturer == "Zlagboard"
    assert board.name == "Pro"
    assert board.facts["subtitle"] == "For all performance levels."
    assert board.facts["productURL"] == "https://zlagboard.com/hangboards"
    assert board.facts["dimensions"] == "25 × 8 × 70.5 cm"
    assert math.isclose(board.facts["aspectRatio"], 70.5 / 25, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert sha256((PACKAGE_ROOT / "assets" / "primary.png").read_bytes()).hexdigest() == (
        EXPECTED_PRIMARY_SHA256
    )
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert len(board.holds) == 28
    assert sum(len(hold.geometry) for hold in board.holds) == 28
    assert Counter(hold.kind for hold in board.holds) == {
        "sloper": 11,
        "edge": 10,
        "pocket": 4,
        "jug": 3,
    }

    for hold in board.holds:
        assert len(hold.geometry) == 1
        assert hold.finger_capacity is None
        assert hold.depth_range_millimeters is None
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert sum(
            command.command == "curve" for command in piece.shape.commands
        ) >= 4
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_piece_is_exact_global_mirror(
            holds[left_id].geometry[0], holds[right_id].geometry[0]
        )

    raw_document = json.loads(
        (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    )
    assert raw_document["schemaVersion"] == 1
    assert not (_keys(raw_document) & FORBIDDEN_KEYS)
    assert "fingerCapacity" not in _keys(raw_document)
    assert "depthRangeMillimeters" not in _keys(raw_document)
