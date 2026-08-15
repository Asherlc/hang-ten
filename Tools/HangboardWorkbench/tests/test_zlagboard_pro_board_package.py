from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))
import board_package  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "zlagboard-pro"
EXPECTED_PRIMARY_SHA256 = (
    "540ef36d327359b564646fa80080298a3ee07b651f1c7ced66ad11773951f148"
)
SURFACE = {"type": "surface"}
DEEP_RECESS = {
    "type": "recess",
    "rimInsetFraction": 0.08,
    "depth": "deep",
}
SHALLOW_RECESS = {
    "type": "recess",
    "rimInsetFraction": 0.08,
    "depth": "shallow",
}
EXPECTED_HOLDS = (
    ("top-jug-left", "jug", None, SURFACE),
    ("top-sloper-32-left", "sloper", None, SURFACE),
    ("top-sloper-20-left", "sloper", None, SURFACE),
    ("top-sloper-jug-center", "jug", None, SURFACE),
    ("top-sloper-20-right", "sloper", None, SURFACE),
    ("top-sloper-32-right", "sloper", None, SURFACE),
    ("top-jug-right", "jug", None, SURFACE),
    ("upper-edge-30-left", "edge", 30, DEEP_RECESS),
    ("upper-sloper-30-left", "sloper", 30, DEEP_RECESS),
    ("upper-sloper-25-left", "sloper", 25, DEEP_RECESS),
    ("upper-edge-35-center", "edge", 35, DEEP_RECESS),
    ("upper-sloper-25-right", "sloper", 25, DEEP_RECESS),
    ("upper-sloper-30-right", "sloper", 30, DEEP_RECESS),
    ("upper-edge-30-right", "edge", 30, DEEP_RECESS),
    ("middle-edge-20-left", "edge", 20, SHALLOW_RECESS),
    ("middle-sloper-25-left", "sloper", 25, DEEP_RECESS),
    ("middle-pocket-30-left", "pocket", 30, DEEP_RECESS),
    ("middle-sloper-30-center", "sloper", 30, DEEP_RECESS),
    ("middle-pocket-30-right", "pocket", 30, DEEP_RECESS),
    ("middle-sloper-25-right", "sloper", 25, DEEP_RECESS),
    ("middle-edge-20-right", "edge", 20, SHALLOW_RECESS),
    ("lower-incut-edge-15-left", "edge", 15, SHALLOW_RECESS),
    ("lower-edge-15-left", "edge", 15, SHALLOW_RECESS),
    ("lower-incut-pocket-30-left", "pocket", 30, DEEP_RECESS),
    ("lower-incut-edge-10-center", "edge", 10, SHALLOW_RECESS),
    ("lower-incut-pocket-30-right", "pocket", 30, DEEP_RECESS),
    ("lower-edge-15-right", "edge", 15, SHALLOW_RECESS),
    ("lower-incut-edge-15-right", "edge", 15, SHALLOW_RECESS),
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


def _png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload[12:16] == b"IHDR"
    return struct.unpack(">II", payload[16:24])


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        (float(point[0]), float(point[1]))
        for field in ("to", "control", "control1", "control2")
        if (point := command.get(field)) is not None
        and isinstance(point, list)
        and len(point) == 2
    )


def _assert_piece_is_exact_global_mirror(
    left: dict[str, object], right: dict[str, object]
) -> None:
    left_frame = left["frame"]
    right_frame = right["frame"]
    assert isinstance(left_frame, dict)
    assert isinstance(right_frame, dict)
    assert right_frame["x"] == pytest.approx(
        1 - left_frame["x"] - left_frame["width"], abs=1e-12
    )
    assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-12)
    assert right_frame["width"] == pytest.approx(left_frame["width"], abs=1e-12)
    assert right_frame["height"] == pytest.approx(left_frame["height"], abs=1e-12)
    assert right["treatment"] == left["treatment"]
    left_commands = left["shape"]["commands"]
    right_commands = right["shape"]["commands"]
    assert [command["command"] for command in right_commands] == [
        command["command"] for command in left_commands
    ]
    for left_command, right_command in zip(left_commands, right_commands, strict=True):
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
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}
    primary_path = PACKAGE_ROOT / "assets" / "primary.png"
    width, height = _png_dimensions(primary_path)

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert width == 2112
    assert height == 745
    assert board["id"] == "zlagboard.pro"
    assert board["manufacturer"] == "Zlagboard"
    assert board["name"] == "Pro"
    assert board["subtitle"] == "For all performance levels."
    assert board["productURL"] == "https://zlagboard.com/hangboards"
    assert board["dimensions"] == "25 × 8 × 70.5 cm"
    assert board["aspectRatio"] == 2.83489932885906
    assert board["aspectRatio"] == pytest.approx(width / height, rel=0, abs=1e-15)
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert sha256(primary_path.read_bytes()).hexdigest() == EXPECTED_PRIMARY_SHA256
    assert tuple(
        (
            hold["id"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold["geometry"][0]["treatment"],
        )
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert len(board["holds"]) == 28
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 28
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "sloper": 11,
        "edge": 10,
        "pocket": 4,
        "jug": 3,
    }
    assert {hold["kind"] for hold in board["holds"]} == {
        "jug",
        "edge",
        "pocket",
        "sloper",
    }

    for hold in board["holds"]:
        assert len(hold["geometry"]) == 1
        assert "fingerCapacity" not in hold
        assert "depthRangeMillimeters" not in hold
        assert "gripType" not in hold
        assert "features" not in hold
        piece = hold["geometry"][0]
        assert piece["shape"]["type"] == "path"
        commands = piece["shape"]["commands"]
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert sum(command["command"] == "curve" for command in commands) >= 4
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        coordinates = [point for command in commands for point in _points(command)]
        assert min(point[0] for point in coordinates) == pytest.approx(0, abs=5e-7)
        assert max(point[0] for point in coordinates) == pytest.approx(1, abs=5e-7)
        assert min(point[1] for point in coordinates) == pytest.approx(0, abs=5e-7)
        assert max(point[1] for point in coordinates) == pytest.approx(1, abs=5e-7)

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_piece_is_exact_global_mirror(
            holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]
        )

    raw_document = json.loads(
        (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    )
    assert raw_document["schemaVersion"] == 1
    assert not (_keys(raw_document) & FORBIDDEN_KEYS)
    assert "fingerCapacity" not in _keys(raw_document)
    assert "depthRangeMillimeters" not in _keys(raw_document)
