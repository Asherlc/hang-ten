from __future__ import annotations

from collections import Counter
from itertools import combinations
import json
import math
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "trango-rock-prodigy-pivot"
EXPECTED_HOLDS = (
    ("upper-sloped-crimp-left", "edge", None, None),
    ("upper-sloped-crimp-right", "edge", None, None),
    ("outer-sloped-crimp-left", "edge", None, None),
    ("outer-sloped-crimp-right", "edge", None, None),
    ("variable-edge-left", "edge", (16, 31), None),
    ("variable-edge-right", "edge", (16, 31), None),
    ("medium-crimp-left", "edge", (9, 10), None),
    ("medium-crimp-right", "edge", (9, 10), None),
    ("large-crimp-left", "edge", (11, 12), None),
    ("large-crimp-right", "edge", (11, 12), None),
    ("two-finger-pocket-left", "pocket", (28, 32), 2),
    ("two-finger-pocket-right", "pocket", (28, 32), 2),
    ("three-finger-pocket-left", "pocket", (17, 28), 3),
    ("three-finger-pocket-right", "pocket", (17, 28), 3),
    ("outer-wedge-pinch-left", "pinch", None, None),
    ("outer-wedge-pinch-right", "pinch", None, None),
    ("lower-sloper-left", "sloper", None, None),
    ("lower-sloper-right", "sloper", None, None),
)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index][0], EXPECTED_HOLDS[index + 1][0])
    for index in range(0, len(EXPECTED_HOLDS), 2)
)

sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_geometry import display_path_for_shape  # noqa: E402


def _command_points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        (float(point[0]), float(point[1]))
        for key, point in command.items()
        if key != "command"
        for point in [point]
        if isinstance(point, list) and len(point) == 2
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return struct.unpack(">II", header[16:24])


def _contains(contour: tuple[tuple[float, float], ...], x: float, y: float) -> bool:
    inside = False
    for first, second in zip(contour, contour[1:]):
        first_x, first_y = first
        second_x, second_y = second
        if (first_y > y) != (second_y > y):
            crossing = (second_x - first_x) * (y - first_y) / (second_y - first_y) + first_x
            if x < crossing:
                inside = not inside
    return inside


def _filled_pixels(
    contour: tuple[tuple[float, float], ...], width: int, height: int
) -> set[int]:
    minimum_x = max(0, math.floor(min(point[0] for point in contour)))
    maximum_x = min(width - 1, math.ceil(max(point[0] for point in contour)) - 1)
    minimum_y = max(0, math.floor(min(point[1] for point in contour)))
    maximum_y = min(height - 1, math.ceil(max(point[1] for point in contour)) - 1)
    return {
        y * width + x
        for y in range(minimum_y, maximum_y + 1)
        for x in range(minimum_x, maximum_x + 1)
        if _contains(contour, x + 0.5, y + 0.5)
    }


def test_trango_rock_prodigy_pivot_preserves_numbered_physical_inventory() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "trango.rock-prodigy-pivot"
    assert board["manufacturer"] == "Trango"
    assert board["name"] == "Rock Prodigy Pivot"
    assert board["productURL"] == "https://trango.com/products/rock-prodigy-pivot?variant=33101615890537"
    assert board["dimensions"] == "15.5 × 5 × 2.5 in"
    width, height = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")
    assert (width, height) == (1774, 887)
    assert board["aspectRatio"] == width / height == 2
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "edge": 10,
        "pocket": 4,
        "pinch": 2,
        "sloper": 2,
    }
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 22

    actual_holds = tuple(
        (
            hold["id"],
            hold["kind"],
            (
                None
                if "depthRangeMillimeters" not in hold
                else (
                    hold["depthRangeMillimeters"]["lowerBound"],
                    hold["depthRangeMillimeters"]["upperBound"],
                )
            ),
            hold.get("fingerCapacity"),
        )
        for hold in board["holds"]
    )
    assert actual_holds == EXPECTED_HOLDS
    assert {
        hold["id"]: len(hold["geometry"])
        for hold in board["holds"]
        if len(hold["geometry"]) != 1
    } == {
        "outer-wedge-pinch-left": 2,
        "outer-wedge-pinch-right": 2,
        "lower-sloper-left": 2,
        "lower-sloper-right": 2,
    }

    for hold in board["holds"]:
        assert "sizeMillimeters" not in hold
        assert "gripType" not in hold
        assert "features" not in hold
        for piece in hold["geometry"]:
            shape = piece["shape"]
            assert shape["type"] == "path"
            commands = shape["commands"]
            command_names = tuple(command["command"] for command in commands)
            assert command_names[0] == "move"
            assert command_names[-1] == "close"
            assert len(command_names[1:-1]) >= 4
            assert set(command_names[1:-1]) == {"curve"}
            frame = piece["frame"]
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            assert frame["width"] * frame["height"] > 0
            points = tuple(
                point for command in commands for point in _command_points(command)
            )
            assert all(0 <= coordinate <= 1 for point in points for coordinate in point)
            assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
            assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
            assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
            assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)

    for left_id, right_id in MIRRORED_PAIRS:
        left_geometry = holds[left_id]["geometry"]
        right_geometry = holds[right_id]["geometry"]
        assert len(right_geometry) == len(left_geometry)
        for left, right in zip(left_geometry, right_geometry, strict=True):
            left_frame = left["frame"]
            right_frame = right["frame"]
            assert right_frame["x"] == pytest.approx(
                1 - left_frame["x"] - left_frame["width"], abs=1e-12
            )
            assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-12)
            assert right_frame["width"] == pytest.approx(
                left_frame["width"], abs=1e-12
            )
            assert right_frame["height"] == pytest.approx(
                left_frame["height"], abs=1e-12
            )
            assert right.get("treatment") == left.get("treatment")
            for left_command, right_command in zip(
                left["shape"]["commands"], right["shape"]["commands"], strict=True
            ):
                assert left_command["command"] == right_command["command"]
                for (left_x, left_y), (right_x, right_y) in zip(
                    _command_points(left_command),
                    _command_points(right_command),
                    strict=True,
                ):
                    assert right_x == pytest.approx(1 - left_x, abs=1e-12)
                    assert right_y == pytest.approx(left_y, abs=1e-12)

    occupied: dict[int, str] = {}
    for hold in board["holds"]:
        for piece_index, piece in enumerate(hold["geometry"]):
            piece_id = f'{hold["id"]}.geometry[{piece_index}]'
            path = display_path_for_shape(
                piece["frame"], piece["shape"], width, height, label=piece_id
            )
            pixels = _filled_pixels(path.contour, width, height)
            assert pixels
            for pixel in pixels:
                assert pixel not in occupied, (
                    f"{piece_id} overlaps {occupied[pixel]} at pixel {pixel}"
                )
                occupied[pixel] = piece_id
    assert len(occupied) > 0

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {"cueStyle", "semantics", "evidence", "artwork", "catalog", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(child) for child in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(child) for child in value))
        return set()

    assert forbidden.isdisjoint(keys(raw))
