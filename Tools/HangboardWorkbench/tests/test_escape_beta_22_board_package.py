from __future__ import annotations

import struct
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "escape-beta-22"
EXPECTED_HOLDS = (
    ("hold-01-left", "Left Thin Pinch", "pinch", None),
    ("hold-01-right", "Right Thin Pinch", "pinch", None),
    ("hold-02-left", "Left Wide Pinch", "pinch", None),
    ("hold-02-right", "Right Wide Pinch", "pinch", None),
    ("hold-03-left", "Left 38mm Mini-Jug", "jug", 38),
    ("hold-03-right", "Right 38mm Mini-Jug", "jug", 38),
    ("hold-04-left", "Left 29mm Incut Jug", "jug", 29),
    ("hold-04-right", "Right 29mm Incut Jug", "jug", 29),
    ("hold-05-left", "Left 12mm Incut Edge", "edge", 12),
    ("hold-05-right", "Right 12mm Incut Edge", "edge", 12),
    ("hold-06-left", "Left 38mm Flat Edge", "edge", 38),
    ("hold-06-right", "Right 38mm Flat Edge", "edge", 38),
    ("hold-07-left", "Left 29mm Flat Edge", "edge", 29),
    ("hold-07-right", "Right 29mm Flat Edge", "edge", 29),
    ("hold-08-left", "Left 12mm Flat Edge", "edge", 12),
    ("hold-08-right", "Right 12mm Flat Edge", "edge", 12),
    ("hold-09-left", "Left 50mm Sloper Edge", "sloper", 50),
    ("hold-09-right", "Right 50mm Sloper Edge", "sloper", 50),
    ("hold-10-left", "Left 31mm Sloper Edge", "sloper", 31),
    ("hold-10-right", "Right 31mm Sloper Edge", "sloper", 31),
    ("hold-11-left", "Left 12mm Sloper Edge", "sloper", 12),
    ("hold-11-right", "Right 12mm Sloper Edge", "sloper", 12),
)
ALLOWED_HOLD_KINDS = {"edge", "jug", "pinch", "sloper"}
CANONICAL_FRAMES = {
    "hold-02-left": {"x": 0.025, "y": 0.49804, "width": 0.12096, "height": 0.14896},
    "hold-02-right": {"x": 0.85404, "y": 0.49804, "width": 0.12096, "height": 0.14896},
    "hold-03-left": {"x": 0.101, "y": 0.346, "width": 0.134, "height": 0.0532},
    "hold-03-right": {"x": 0.765, "y": 0.346, "width": 0.134, "height": 0.0532},
}
REVIEWED_ABSOLUTE_POINTS = {
    "hold-02-left": (
        (0.027520000000000003, 0.5071599999999999),
        (0.14596, 0.49804),
        (0.06028000000000001, 0.52844),
        (0.0943, 0.5254),
        (0.12958, 0.6318),
        (0.12832, 0.54972),
        (0.11824000000000001, 0.59532),
        (0.03256, 0.6166),
        (0.1006, 0.647),
        (0.04894, 0.647),
        (0.027520000000000003, 0.5071599999999999),
        (0.025, 0.58468),
        (0.025, 0.53908),
    ),
    "hold-02-right": (
        (0.97248, 0.5071599999999999),
        (0.85404, 0.49804),
        (0.93972, 0.52844),
        (0.9057, 0.5254),
        (0.87042, 0.6318),
        (0.87168, 0.54972),
        (0.88176, 0.59532),
        (0.96744, 0.6166),
        (0.8994, 0.647),
        (0.95106, 0.647),
        (0.97248, 0.5071599999999999),
        (0.975, 0.58468),
        (0.975, 0.53908),
    ),
    "hold-03-left": (
        (0.1077, 0.38799999999999996),
        (0.22562000000000001, 0.35831999999999997),
        (0.12512, 0.36279999999999996),
        (0.18810000000000002, 0.346),
        (0.22294000000000003, 0.38408),
        (0.23500000000000001, 0.3656),
        (0.23366, 0.37848),
        (0.1077, 0.3992),
        (0.18810000000000002, 0.3712),
        (0.13316, 0.38632),
        (0.1077, 0.38799999999999996),
        (0.101, 0.39696),
        (0.101, 0.39192),
    ),
    "hold-03-right": (
        (0.8923, 0.38799999999999996),
        (0.7743800000000001, 0.35831999999999997),
        (0.87488, 0.36279999999999996),
        (0.8119000000000001, 0.346),
        (0.77706, 0.38408),
        (0.765, 0.3656),
        (0.76634, 0.37848),
        (0.8923, 0.3992),
        (0.8119000000000001, 0.3712),
        (0.86684, 0.38632),
        (0.8923, 0.38799999999999996),
        (0.899, 0.39696),
        (0.899, 0.39192),
    ),
}
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


def _points(command: Mapping[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def test_escape_beta_22_audited_package_contract() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    width, height = struct.unpack(
        ">II", (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()[16:24]
    )
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {item.name for item in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {item.name for item in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert (width, height) == (1536, 1024)

    assert board["id"] == "escape-beta-22"
    assert board["manufacturer"] == "Escape Climbing"
    assert board["name"] == "Beta Board"
    assert board["dimensions"] == "26 × 6 × 2 in"
    assert board["aspectRatio"] == pytest.approx(width / height, rel=0, abs=1e-12)
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert board["productURL"] == "https://escapeclimbing.com/products/ec72100"
    assert tuple(
        (hold["id"], hold["name"], hold["kind"], hold.get("sizeMillimeters"))
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert len(board["holds"]) == 22
    assert {hold["kind"] for hold in board["holds"]} <= ALLOWED_HOLD_KINDS
    assert {kind: sum(hold["kind"] == kind for hold in board["holds"]) for kind in ALLOWED_HOLD_KINDS} == {
        "edge": 8,
        "jug": 4,
        "pinch": 4,
        "sloper": 6,
    }

    for hold in board["holds"]:
        assert "depthRangeMillimeters" not in hold
        assert "gripType" not in hold
        assert "fingerCapacity" not in hold
        assert "features" not in hold

        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        assert "treatment" not in piece
        assert piece["shape"]["type"] == "path"
        commands = piece["shape"]["commands"]
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert 0 <= piece["frame"]["x"] <= 1
        assert 0 <= piece["frame"]["y"] <= 1
        assert 0 <= piece["frame"]["x"] + piece["frame"]["width"] <= 1
        assert 0 <= piece["frame"]["y"] + piece["frame"]["height"] <= 1
        for point in (point for command in commands for point in _points(command)):
            assert 0 <= point[0] <= 1
            assert 0 <= point[1] <= 1

        if hold["id"] in CANONICAL_FRAMES:
            assert piece["frame"] == CANONICAL_FRAMES[hold["id"]]
            local_points = tuple(
                point for command in commands for point in _points(command)
            )
            assert min(point[0] for point in local_points) == 0
            assert max(point[0] for point in local_points) == 1
            assert min(point[1] for point in local_points) == 0
            assert max(point[1] for point in local_points) == 1
            assert tuple(
                (
                    piece["frame"]["x"] + piece["frame"]["width"] * local_x,
                    piece["frame"]["y"] + piece["frame"]["height"] * local_y,
                )
                for local_x, local_y in local_points
            ) == REVIEWED_ABSOLUTE_POINTS[hold["id"]]

        family = int(hold["id"].split("-")[1])
        if family <= 8:
            assert [command["command"] for command in commands] == [
                "move",
                "curve",
                "curve",
                "curve",
                "curve",
                "close",
            ]
        else:
            assert [command["command"] for command in commands] == [
                "move",
                "curve",
                "line",
                "curve",
                "curve",
                "close",
            ]

    for family in range(1, 12):
        left = holds[f"hold-{family:02d}-left"]["geometry"][0]
        right = holds[f"hold-{family:02d}-right"]["geometry"][0]
        assert right["frame"]["x"] == pytest.approx(
            1 - left["frame"]["x"] - left["frame"]["width"], abs=1e-12
        )
        assert right["frame"]["y"] == pytest.approx(left["frame"]["y"], abs=1e-12)
        assert right["frame"]["width"] == pytest.approx(
            left["frame"]["width"], abs=1e-12
        )
        assert right["frame"]["height"] == pytest.approx(
            left["frame"]["height"], abs=1e-12
        )
        for left_command, right_command in zip(
            left["shape"]["commands"], right["shape"]["commands"], strict=True
        ):
            assert right_command["command"] == left_command["command"]
            left_points = _points(left_command)
            right_points = _points(right_command)
            assert len(right_points) == len(left_points)
            for (left_x, left_y), (right_x, right_y) in zip(
                left_points, right_points, strict=True
            ):
                assert right_x == pytest.approx(1 - left_x, abs=1e-12)
                assert right_y == pytest.approx(left_y, abs=1e-12)
