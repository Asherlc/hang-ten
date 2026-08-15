from __future__ import annotations

from collections import Counter
import json
import struct
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "target10a-linebreaker-base"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


EXPECTED_HOLDS = (
    ("jug-left", "jug", None, None, None, 1),
    ("sloper-32-5-left", "sloper", None, None, "sloper", 1),
    ("sloper-22-5-center", "sloper", None, None, "sloper", 1),
    ("sloper-32-5-right", "sloper", None, None, "sloper", 1),
    ("jug-right", "jug", None, None, None, 1),
    ("edge-16-left", "edge", 16, 4, None, 1),
    ("pocket-28-left", "pocket", 28, 3, "threeFingerPocket", 1),
    ("pocket-28-right", "pocket", 28, 3, "threeFingerPocket", 1),
    ("edge-16-right", "edge", 16, 4, None, 1),
    ("pocket-37-left", "pocket", 37, 4, "fourFingerPocket", 1),
    ("pocket-45-left", "pocket", 45, 3, "threeFingerPocket", 1),
    ("pocket-50-left", "pocket", 50, 2, "twoFingerPocket", 1),
    ("sloper-bar-35-center", "sloper", 35, None, "sloper", 1),
    ("pocket-50-right", "pocket", 50, 2, "twoFingerPocket", 1),
    ("pocket-45-right", "pocket", 45, 3, "threeFingerPocket", 1),
    ("pocket-37-right", "pocket", 37, 4, "fourFingerPocket", 1),
    ("pocket-30-left", "pocket", 30, 2, "twoFingerPocket", 1),
    ("pocket-24-left", "pocket", 24, 2, "twoFingerPocket", 1),
    ("edge-20-left", "edge", 20, 4, None, 1),
    ("edge-18-left", "edge", 18, 3, None, 1),
    ("edge-18-right", "edge", 18, 3, None, 1),
    ("edge-20-right", "edge", 20, 4, None, 1),
    ("pocket-24-right", "pocket", 24, 2, "twoFingerPocket", 1),
    ("pocket-30-right", "pocket", 30, 2, "twoFingerPocket", 1),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-32-5-left", "sloper-32-5-right"),
    ("edge-16-left", "edge-16-right"),
    ("pocket-28-left", "pocket-28-right"),
    ("pocket-37-left", "pocket-37-right"),
    ("pocket-45-left", "pocket-45-right"),
    ("pocket-50-left", "pocket-50-right"),
    ("pocket-30-left", "pocket-30-right"),
    ("pocket-24-left", "pocket-24-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-18-left", "edge-18-right"),
)


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key, point in command.items()
        if key != "command" and point is not None
    )


def _global_points(piece: dict[str, object]) -> tuple[tuple[float, float], ...]:
    frame = piece["frame"]
    assert isinstance(frame, dict)
    return tuple(
        (
            frame["x"] + frame["width"] * x,
            frame["y"] + frame["height"] * y,
        )
        for command in piece["shape"]["commands"]
        for x, y in _points(command)
    )


def _assert_exact_global_mirror(
    left: dict[str, object], right: dict[str, object]
) -> None:
    left_frame = left["frame"]
    right_frame = right["frame"]
    assert isinstance(left_frame, dict) and isinstance(right_frame, dict)
    assert right_frame["x"] == pytest.approx(
        1 - left_frame["x"] - left_frame["width"], abs=1e-12
    )
    assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-12)
    assert right_frame["width"] == pytest.approx(left_frame["width"], abs=1e-12)
    assert right_frame["height"] == pytest.approx(left_frame["height"], abs=1e-12)
    assert right.get("treatment") == left.get("treatment")
    assert [command["command"] for command in right["shape"]["commands"]] == [
        command["command"] for command in left["shape"]["commands"]
    ]
    for (left_x, left_y), (right_x, right_y) in zip(
        _global_points(left), _global_points(right), strict=True
    ):
        assert right_x == pytest.approx(1 - left_x, abs=1e-12)
        assert right_y == pytest.approx(left_y, abs=1e-12)


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return struct.unpack(">II", header[16:24])


def test_target10a_linebreaker_base_preserves_the_manufacturer_hold_map() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert board_package._HOLD_KINDS == frozenset(
        {"jug", "edge", "pocket", "pinch", "sloper"}
    )
    assert board["id"] == "target10a-linebreaker-base"
    assert board["manufacturer"] == "target10a"
    assert board["name"] == "Linebreaker BASE"
    assert board["dimensions"] == "58 × 15 × 5.5 cm"
    assert board["aspectRatio"] == pytest.approx(4 / 3, abs=1e-12)
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(
        (
            hold["id"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
            hold.get("gripType"),
            len(hold["geometry"]),
        )
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "jug": 2,
        "sloper": 4,
        "edge": 6,
        "pocket": 12,
    }
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 24

    for hold in board["holds"]:
        assert "depthRangeMillimeters" not in hold
        assert "features" not in hold
        for piece in hold["geometry"]:
            shape = piece["shape"]
            frame = piece["frame"]
            assert shape["type"] == "path"
            assert shape["commands"][0]["command"] == "move"
            assert shape["commands"][-1]["command"] == "close"
            assert any(command["command"] == "curve" for command in shape["commands"])
            assert min(
                x for command in shape["commands"] for x, _ in _points(command)
            ) == 0
            assert min(
                y for command in shape["commands"] for _, y in _points(command)
            ) == 0
            assert max(
                x for command in shape["commands"] for x, _ in _points(command)
            ) == 1
            assert max(
                y for command in shape["commands"] for _, y in _points(command)
            ) == 1
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            assert frame["width"] * frame["height"] > 0

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_exact_global_mirror(
            holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]
        )

    for center_id in ("sloper-22-5-center", "sloper-bar-35-center"):
        frame = holds[center_id]["geometry"][0]["frame"]
        assert frame["x"] + frame["width"] / 2 == pytest.approx(0.5, abs=1e-12)


def test_target10a_linebreaker_base_is_a_closed_direct_child_package() -> None:
    package_entries = {path.name for path in PACKAGE_ROOT.iterdir()}
    asset_entries = {path.name for path in (PACKAGE_ROOT / "assets").iterdir()}
    assert package_entries == {"board.json", "assets"}
    assert asset_entries == {"primary.png"}

    document = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden_keys = {
        "artwork", "claims", "cueStyle", "evidence", "semantics", "sourceAudit", "ui"
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(document))


def test_target10a_linebreaker_base_keeps_32_5_slopers_on_the_visible_full_canvas_plane() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    raster_width, raster_height = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")
    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    document = json.loads(raw_document)
    numeric_tokens = json.loads(raw_document, parse_float=str)
    holds = {hold["id"]: hold for hold in package.board["holds"]}

    assert (raster_width, raster_height) == (1448, 1086)
    assert numeric_tokens["aspectRatio"] == "1.33333333333333"
    assert document["aspectRatio"] == pytest.approx(
        raster_width / raster_height, abs=1e-12
    )
    for hold_id in ("sloper-32-5-left", "sloper-32-5-right"):
        frame = holds[hold_id]["geometry"][0]["frame"]
        assert round(frame["y"] * raster_height) == 387
        assert round((frame["y"] + frame["height"]) * raster_height) == 441
