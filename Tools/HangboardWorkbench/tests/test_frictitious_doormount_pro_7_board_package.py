from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "frictitious-doormount-pro-7"
EXPECTED_HOLDS = (
    ("pull-up-jug", "jug", None, 1),
    ("edge-35", "edge", 35, 2),
    ("edge-25", "edge", 25, 2),
    ("pockets", "pocket", None, 2),
    ("edge-20", "edge", 20, 2),
    ("edge-15", "edge", 15, 2),
    ("edge-10", "edge", 10, 2),
)
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(command[key])
        for key in ("to", "control", "control1", "control2")
        if key in command
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def test_frictitious_doormount_pro_7_preserves_seven_audited_holds() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "frictitious-doormount-pro-7"
    assert board["manufacturer"] == "Frictitious Climbing"
    assert board["name"] == "DoorMount Pro 7"
    assert board["dimensions"] == "25.5 × 4.5 × 2.25 in"
    width, height = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")
    assert board["aspectRatio"] == pytest.approx(width / height)
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(
        (
            hold["id"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            len(hold["geometry"]),
        )
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "edge": 5,
        "jug": 1,
        "pocket": 1,
    }

    for hold in board["holds"]:
        for piece in hold["geometry"]:
            commands = piece["shape"]["commands"]
            assert piece["shape"]["type"] == "path"
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            assert any(command["command"] == "curve" for command in commands)
            frame = piece["frame"]
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            assert frame["width"] * frame["height"] > 0
            assert piece.get("treatment") is None
            local_points = [point for command in commands for point in _points(command)]
            assert min(point[0] for point in local_points) == pytest.approx(0)
            assert max(point[0] for point in local_points) == pytest.approx(1)
            assert min(point[1] for point in local_points) == pytest.approx(0)
            assert max(point[1] for point in local_points) == pytest.approx(1)
        assert hold.get("depthRangeMillimeters") is None
        assert hold.get("gripType") is None
        assert hold.get("fingerCapacity") is None
        assert hold.get("features") is None

    for hold_id in ("edge-35", "edge-25", "pockets", "edge-20", "edge-15", "edge-10"):
        left, right = holds[hold_id]["geometry"]
        assert right["frame"]["x"] == pytest.approx(
            1 - left["frame"]["x"] - left["frame"]["width"], abs=1e-12
        )
        assert right["frame"]["y"] == pytest.approx(left["frame"]["y"], abs=1e-12)
        assert right["frame"]["width"] == pytest.approx(left["frame"]["width"], abs=1e-12)
        assert right["frame"]["height"] == pytest.approx(left["frame"]["height"], abs=1e-12)
        assert [command["command"] for command in right["shape"]["commands"]] == [
            command["command"] for command in left["shape"]["commands"]
        ]
        for left_command, right_command in zip(
            left["shape"]["commands"], right["shape"]["commands"], strict=True
        ):
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    jug = holds["pull-up-jug"]["geometry"][0]
    assert jug["frame"]["x"] == pytest.approx(
        1 - jug["frame"]["x"] - jug["frame"]["width"]
    )
    assert jug["frame"]["width"] > 0.85

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    forbidden_keys = {
        "artwork",
        "catalog",
        "claims",
        "cueStyle",
        "evidence",
        "semantics",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(raw_document))
