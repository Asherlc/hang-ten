from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "nature-stoak-board-iii"
EXPECTED_HOLDS = (
    ("comfortable-jug-left", "jug", None),
    ("comfortable-jug-right", "jug", None),
    ("gradient-edge-10-25-left", "edge", None),
    ("gradient-edge-10-25-right", "edge", None),
    ("granite-edge-20-left", "edge", 20),
    ("granite-edge-20-right", "edge", 20),
    ("wood-edge-30-left", "edge", 30),
    ("wood-edge-30-right", "edge", 30),
    ("center-open-hand-55", "jug", 55),
    ("center-edge-22", "edge", 22),
    ("center-granite-edge-30", "edge", 30),
)
MIRRORED_PAIRS = (
    ("comfortable-jug-left", "comfortable-jug-right"),
    ("gradient-edge-10-25-left", "gradient-edge-10-25-right"),
    ("granite-edge-20-left", "granite-edge-20-right"),
    ("wood-edge-30-left", "wood-edge-30-right"),
)
SUPPORTED_KINDS = {"jug", "edge", "pocket", "pinch", "sloper"}
sys.path.insert(0, str(WORKBENCH_ROOT))

from board_package import load_board_package  # noqa: E402


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(command[key])
        for key in ("to", "control", "control1", "control2")
        if command.get(key) is not None
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return struct.unpack(">II", header[16:24])


def test_stoak_board_iii_preserves_official_inventory_and_exact_geometry() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board["id"] == "nature-climbing.stoak-board-iii"
    assert board["manufacturer"] == "Nature Climbing"
    assert board["name"] == "Stoak Board III"
    assert board["dimensions"] == "57 × 12 × 5.5 cm"
    image_width, image_height = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")
    assert math.isclose(
        board["aspectRatio"], image_width / image_height, rel_tol=0.001
    )
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(
        (hold["id"], hold["kind"], hold.get("sizeMillimeters"))
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "edge": 8,
        "jug": 3,
    }
    assert {hold["kind"] for hold in board["holds"]} <= SUPPORTED_KINDS

    for hold in board["holds"]:
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        shape = piece["shape"]
        commands = shape["commands"]
        assert shape["type"] == "path"
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert any(command["command"] == "curve" for command in commands)
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        points = tuple(point for command in commands for point in _points(command))
        assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
        assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
        assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
        assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]["geometry"][0]
        right = holds[right_id]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]
        assert math.isclose(
            right_frame["x"],
            1 - left_frame["x"] - left_frame["width"],
            abs_tol=1e-12,
        )
        assert right_frame["y"] == left_frame["y"]
        assert right_frame["width"] == left_frame["width"]
        assert right_frame["height"] == left_frame["height"]
        assert right["treatment"] == left["treatment"]
        for left_command, right_command in zip(
            left["shape"]["commands"], right["shape"]["commands"], strict=True
        ):
            assert left_command["command"] == right_command["command"]
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    for hold_id in (
        "gradient-edge-10-25-left",
        "gradient-edge-10-25-right",
    ):
        depth_range = holds[hold_id]["depthRangeMillimeters"]
        assert (depth_range["lowerBound"], depth_range["upperBound"]) == (10, 25)
    assert holds["center-open-hand-55"]["gripType"] == "openHand"
    assert all("fingerCapacity" not in hold for hold in board["holds"])
    assert all("features" not in hold for hold in board["holds"])

    for hold_id in (
        "center-open-hand-55",
        "center-edge-22",
        "center-granite-edge-30",
    ):
        frame = holds[hold_id]["geometry"][0]["frame"]
        assert math.isclose(frame["x"], 1 - frame["x"] - frame["width"], abs_tol=1e-12)


def test_stoak_board_iii_excludes_nonphysical_package_data() -> None:
    load_board_package(PACKAGE_ROOT)
    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")

    for forbidden in (
        "cueStyle",
        "semantics",
        "evidence",
        "claims",
        "features",
        "fingerCapacity",
        "shortLabel",
        "detail",
    ):
        assert forbidden not in raw_document
