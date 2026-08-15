from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import struct
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "Tools" / "HangboardWorkbench"))

import board_package


PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-climbers-edge"
EXPECTED_HOLDS = (
    "jug-left",
    "sloper-flat-left",
    "sloper-round-center",
    "sloper-flat-right",
    "jug-right",
    "edge-20-left",
    "edge-15-left",
    "edge-10-center",
    "edge-15-right",
    "edge-20-right",
    "edge-17-5-left",
    "edge-12-5-left",
    "edge-7-5-center",
    "edge-12-5-right",
    "edge-17-5-right",
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-flat-left", "sloper-flat-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-15-left", "edge-15-right"),
    ("edge-17-5-left", "edge-17-5-right"),
    ("edge-12-5-left", "edge-12-5-right"),
)


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for point in (
            command.get("to"),
            command.get("control"),
            command.get("control1"),
            command.get("control2"),
        )
        if point is not None
    )


def test_metolius_climbers_edge_audited_inventory_and_exact_geometry() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "metolius.climbers-edge"
    assert board["manufacturer"] == "Metolius"
    assert board["name"] == "Climbers Edge Board"
    assert board["dimensions"] == "600 × 160 mm"
    image_width, image_height = struct.unpack(
        ">II", (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()[16:24]
    )
    assert (image_width, image_height) == (1717, 916)
    assert board["aspectRatio"] == 1.87445414847162
    assert board["aspectRatio"] == pytest.approx(1717 / 916)
    assert board["aspectRatio"] == pytest.approx(image_width / image_height)
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert package.hold_ids == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in holds.values()) == {
        "edge": 10,
        "sloper": 3,
        "jug": 2,
    }

    assert holds["jug-left"]["features"] == ["jug"]
    assert holds["jug-right"]["features"] == ["jug"]
    assert holds["sloper-round-center"]["features"] == ["roundSloper"]
    assert all(
        holds[hold_id]["gripType"] == "sloper"
        for hold_id in (
            "sloper-flat-left",
            "sloper-round-center",
            "sloper-flat-right",
        )
    )
    assert {
        hold_id: holds[hold_id]["sizeMillimeters"]
        for hold_id in (
            "edge-20-left",
            "edge-20-right",
            "edge-15-left",
            "edge-15-right",
            "edge-10-center",
        )
    } == {
        "edge-20-left": 20,
        "edge-20-right": 20,
        "edge-15-left": 15,
        "edge-15-right": 15,
        "edge-10-center": 10,
    }
    assert all(
        "sizeMillimeters" not in holds[hold_id]
        for hold_id in (
            "edge-17-5-left",
            "edge-17-5-right",
            "edge-12-5-left",
            "edge-12-5-right",
            "edge-7-5-center",
        )
    )
    assert all("fingerCapacity" not in hold for hold in holds.values())
    assert all("depthRangeMillimeters" not in hold for hold in holds.values())

    for hold in holds.values():
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        commands = piece["shape"]["commands"]
        frame = piece["frame"]
        assert piece["shape"]["type"] == "path"
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert any(command["command"] == "curve" for command in commands)
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0

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
        for left_command, right_command in zip(
            left["shape"]["commands"], right["shape"]["commands"], strict=True
        ):
            assert left_command["command"] == right_command["command"]
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    top_ids = (
        "jug-left",
        "sloper-flat-left",
        "sloper-round-center",
        "sloper-flat-right",
        "jug-right",
    )
    for left_id, right_id in zip(top_ids, top_ids[1:]):
        left_frame = package.hold_frame(left_id)
        right_frame = package.hold_frame(right_id)
        assert math.isclose(
            left_frame.x + left_frame.width,
            right_frame.x,
            abs_tol=1e-12,
        )

    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    for forbidden in ("cueStyle", "evidence", "claims", "shortLabel", "detail"):
        assert forbidden not in raw_document
