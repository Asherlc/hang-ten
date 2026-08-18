from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "trango-rock-prodigy-pivot"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_geometry  # noqa: E402
import board_package  # noqa: E402


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
ALLOWED_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
EXPECTED_KIND_COUNTS = Counter({"edge": 10, "pocket": 4, "pinch": 2, "sloper": 2})
EXPECTED_PIECE_COUNT = 22
EXPECTED_PIXEL_SIZE = (1774, 887)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index][0], EXPECTED_HOLDS[index + 1][0])
    for index in range(0, len(EXPECTED_HOLDS), 2)
)
FORBIDDEN_RAW_KEYS = frozenset(
    {"cueStyle", "semantics", "evidence", "artwork", "catalog", "claims", "ui"}
)


def _command_points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(child) for child in value))
    return set()


def test_trango_rock_prodigy_pivot_package_preserves_reviewed_inventory_and_geometry() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}
    image_path = PACKAGE_ROOT / "assets" / "primary.png"
    width, height = board_package._png_dimensions(image_path)

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "trango.rock-prodigy-pivot"
    assert board["manufacturer"] == "Trango"
    assert board["name"] == "Rock Prodigy Pivot"
    assert board["dimensions"] == "15.5 × 5 × 2.5 in"
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert (width, height) == EXPECTED_PIXEL_SIZE
    assert board["aspectRatio"] == width / height
    assert board_package._HOLD_KINDS == ALLOWED_KINDS
    assert all(hold["kind"] in ALLOWED_KINDS for hold in board["holds"])
    assert Counter(hold["kind"] for hold in board["holds"]) == EXPECTED_KIND_COUNTS

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
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == EXPECTED_PIECE_COUNT
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
        assert {"sizeMillimeters", "gripType", "features"}.isdisjoint(hold)
        for piece_index, piece in enumerate(hold["geometry"]):
            label = f"{hold['id']}.geometry[{piece_index}]"
            shape = piece["shape"]
            assert shape["type"] == "path"
            commands = shape["commands"]
            assert commands[0]["command"] == "move"
            assert commands[-1] == {"command": "close"}
            assert len(commands[1:-1]) >= 4
            assert {command["command"] for command in commands[1:-1]} == {"curve"}
            min_x, max_x, min_y, max_y = board_geometry.flattened_shape_bounds(commands)
            assert min_x == pytest.approx(0, abs=5e-7)
            assert min_y == pytest.approx(0, abs=5e-7)
            assert max_x == pytest.approx(1, abs=5e-7)
            assert max_y == pytest.approx(1, abs=5e-7)
            path = board_geometry.display_path_for_shape(
                piece["frame"], piece["shape"], width, height, label=label
            )
            assert path.commands[0][0] == "M"
            assert path.commands[-1][0] == "Z"
            assert path.data.endswith(" Z")

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
            assert right_frame["y"] == left_frame["y"]
            assert right_frame["width"] == left_frame["width"]
            assert right_frame["height"] == left_frame["height"]
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

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    assert FORBIDDEN_RAW_KEYS.isdisjoint(_all_keys(raw))
