from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "yy-verticalboard-evo"
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

from board_package import load_board_package  # noqa: E402


EXPECTED_HOLDS = (
    ("jug-left", "jug"),
    ("jug-right", "jug"),
    ("sloper-43-left", "sloper"),
    ("sloper-43-right", "sloper"),
    ("sloper-38-left", "sloper"),
    ("sloper-38-right", "sloper"),
    ("sloper-30-center", "sloper"),
    ("edge-25-left", "edge"),
    ("edge-25-right", "edge"),
    ("edge-20-left", "edge"),
    ("edge-20-right", "edge"),
    ("edge-18-left", "edge"),
    ("edge-18-right", "edge"),
    ("edge-40-center", "edge"),
    ("edge-inclined-30-left", "edge"),
    ("edge-inclined-30-right", "edge"),
    ("pocket-20-two-left", "pocket"),
    ("pocket-20-two-right", "pocket"),
    ("pocket-inclined-25-two-left", "pocket"),
    ("pocket-inclined-25-two-right", "pocket"),
    ("pocket-mono-one-phalanx-left", "pocket"),
    ("pocket-mono-one-phalanx-right", "pocket"),
    ("pocket-mono-two-phalanges-left", "pocket"),
    ("pocket-mono-two-phalanges-right", "pocket"),
    ("handle-center", "jug"),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-43-left", "sloper-43-right"),
    ("sloper-38-left", "sloper-38-right"),
    ("edge-25-left", "edge-25-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-18-left", "edge-18-right"),
    ("edge-inclined-30-left", "edge-inclined-30-right"),
    ("pocket-20-two-left", "pocket-20-two-right"),
    ("pocket-inclined-25-two-left", "pocket-inclined-25-two-right"),
    ("pocket-mono-one-phalanx-left", "pocket-mono-one-phalanx-right"),
    ("pocket-mono-two-phalanges-left", "pocket-mono-two-phalanges-right"),
)
DEPTHS = {
    "edge-25-left": 25,
    "edge-25-right": 25,
    "edge-20-left": 20,
    "edge-20-right": 20,
    "edge-18-left": 18,
    "edge-18-right": 18,
    "edge-40-center": 40,
    "edge-inclined-30-left": 30,
    "edge-inclined-30-right": 30,
    "pocket-20-two-left": 20,
    "pocket-20-two-right": 20,
    "pocket-inclined-25-two-left": 25,
    "pocket-inclined-25-two-right": 25,
}
FINGER_CAPACITIES = {
    "pocket-20-two-left": 2,
    "pocket-20-two-right": 2,
    "pocket-inclined-25-two-left": 2,
    "pocket-inclined-25-two-right": 2,
    "pocket-mono-one-phalanx-left": 1,
    "pocket-mono-one-phalanx-right": 1,
    "pocket-mono-two-phalanges-left": 1,
    "pocket-mono-two-phalanges-right": 1,
}


def _png_dimensions(path: Path) -> tuple[int, int]:
    signature = path.read_bytes()[:24]
    assert signature[:8] == b"\x89PNG\r\n\x1a\n"
    assert signature[12:16] == b"IHDR"
    return struct.unpack(">II", signature[16:24])


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)  # type: ignore[arg-type]
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _assert_exact_global_mirror(
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
    assert right.get("treatment") == left.get("treatment")
    left_shape = left["shape"]
    right_shape = right["shape"]
    assert isinstance(left_shape, dict)
    assert isinstance(right_shape, dict)
    left_commands = left_shape["commands"]
    right_commands = right_shape["commands"]
    assert isinstance(left_commands, list)
    assert isinstance(right_commands, list)
    assert [command["command"] for command in right_commands] == [
        command["command"] for command in left_commands
    ]
    for left_command, right_command in zip(left_commands, right_commands, strict=True):
        assert isinstance(left_command, dict)
        assert isinstance(right_command, dict)
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def _recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_recursive_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_recursive_keys(child) for child in value))
    return set()


def test_yy_verticalboard_evo_preserves_audited_inventory_and_geometry() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}
    image_width, image_height = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert (image_width, image_height) == (1774, 887)
    assert board["id"] == "yy.verticalboard-evo"
    assert board["manufacturer"] == "YY Vertical"
    assert board["name"] == "VerticalBoard Evo"
    assert board["dimensions"] == "65 × 14 × 5.5 cm"
    assert board["aspectRatio"] == 2.0
    assert board["aspectRatio"] == image_width / image_height
    assert board["productURL"] == (
        "https://www.yyvertical.com/en/collections/entrainement/products/"
        "verticalboard-evo"
    )
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert tuple((hold["id"], hold["kind"]) for hold in board["holds"]) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "jug": 3,
        "edge": 9,
        "pocket": 8,
        "sloper": 5,
    }

    assert {hold_id: holds[hold_id]["sizeMillimeters"] for hold_id in DEPTHS} == DEPTHS
    assert {
        hold_id: holds[hold_id]["fingerCapacity"] for hold_id in FINGER_CAPACITIES
    } == FINGER_CAPACITIES
    assert all(
        "sizeMillimeters" not in hold
        for hold in board["holds"]
        if hold["id"] not in DEPTHS
    )
    assert all(
        "fingerCapacity" not in hold
        for hold in board["holds"]
        if hold["id"] not in FINGER_CAPACITIES
    )
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])
    assert all("gripType" not in hold for hold in board["holds"])
    assert all("features" not in hold for hold in board["holds"])

    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 25
    for hold in board["holds"]:
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        shape = piece["shape"]
        commands = shape["commands"]
        assert shape["type"] == "path"
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert len(commands) >= 6
        assert {command["command"] for command in commands} == {"move", "curve", "close"}
        assert all(
            0 <= coordinate <= 1
            for command in commands
            for point in _points(command)
            for coordinate in point
        )
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_exact_global_mirror(
            holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]
        )

    for center_id in ("sloper-30-center", "edge-40-center", "handle-center"):
        frame = holds[center_id]["geometry"][0]["frame"]
        assert frame["x"] + frame["width"] / 2 == pytest.approx(0.5, abs=1e-12)
    assert holds["sloper-30-center"]["geometry"][0]["frame"]["y"] < holds["edge-40-center"]["geometry"][0]["frame"]["y"]
    assert holds["edge-40-center"]["geometry"][0]["frame"]["y"] < holds["handle-center"]["geometry"][0]["frame"]["y"]
    assert holds["handle-center"]["geometry"][0]["frame"]["width"] > holds["edge-40-center"]["geometry"][0]["frame"]["width"]

    assert all(hold["geometry"][0]["frame"]["x"] >= 0.03 for hold in board["holds"])
    assert all(
        hold["geometry"][0]["frame"]["x"] + hold["geometry"][0]["frame"]["width"] <= 0.97
        for hold in board["holds"]
    )
    assert all(hold["geometry"][0]["frame"]["y"] >= 0.28 for hold in board["holds"])
    assert all(
        hold["geometry"][0]["frame"]["y"] + hold["geometry"][0]["frame"]["height"] <= 0.69
        for hold in board["holds"]
    )

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text("utf-8"))
    forbidden = {
        "artwork",
        "catalog",
        "claims",
        "cueStyle",
        "evidence",
        "semantics",
    }
    assert forbidden.isdisjoint(_recursive_keys(raw_document))
