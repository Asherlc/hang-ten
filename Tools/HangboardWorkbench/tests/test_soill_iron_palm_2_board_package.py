from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "soill-iron-palm-2"
PRESENTATION_SIZE = (1536, 1024)
FOUNDATION_HOLD_KINDS = {"jug", "edge", "pocket", "pinch", "sloper"}
EXPECTED_HOLDS = (
    ("sloper-left", "Left big sloper", "sloper", None, 1),
    ("sloper-right", "Right big sloper", "sloper", None, 1),
    ("pinch-left", "Left 3 in pinch", "pinch", None, 2),
    ("pinch-right", "Right 3 in pinch", "pinch", None, 2),
    ("top-jug-rail", "Top incut jug rail", "jug", None, 1),
    ("rounded-edge-40", "40 mm rounded edge", "edge", 40, 1),
    ("flat-edge-35", "35 mm flat edge", "edge", 35, 1),
    ("flat-edge-15", "15 mm flat edge", "edge", 15, 1),
)
EXPECTED_PIXEL_FRAMES = {
    "sloper-left": ((84, 218, 385, 326.7),),
    "sloper-right": ((1067, 218, 385, 326.7),),
    "pinch-left": ((42, 546.34, 231, 271.66), (144, 710, 139, 147)),
    "pinch-right": ((1263, 546.34, 231, 271.66), (1253, 710, 139, 147)),
    "top-jug-rail": ((434, 381, 668, 27),),
    "rounded-edge-40": ((432, 452, 672, 48),),
    "flat-edge-35": ((368, 555, 800, 46),),
    "flat-edge-15": ((321, 665, 894, 73),),
}

sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        assert image.read(8) == b"\x89PNG\r\n\x1a\n"
        assert image.read(4) == b"\x00\x00\x00\r"
        assert image.read(4) == b"IHDR"
        return struct.unpack(">II", image.read(8))


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def test_soill_iron_palm_2_preserves_audited_contacts_and_symmetry() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "soill.iron-palm-2"
    assert board["manufacturer"] == "So iLL"
    assert board["name"] == "Iron Palm 2.0"
    assert board["dimensions"] == "27 × 11.5 × 4 in"
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert _png_dimensions(PACKAGE_ROOT / board["presentation"]["assetPath"]) == PRESENTATION_SIZE
    image_aspect_ratio = PRESENTATION_SIZE[0] / PRESENTATION_SIZE[1]
    assert math.isclose(
        board["aspectRatio"],
        image_aspect_ratio,
        rel_tol=0.001,
        abs_tol=0.0,
    )

    assert board_package._HOLD_KINDS == FOUNDATION_HOLD_KINDS
    assert len(board["holds"]) == 8
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 10
    assert Counter(hold["kind"] for hold in board["holds"]) == Counter(
        {"sloper": 2, "pinch": 2, "jug": 1, "edge": 3}
    )
    assert tuple(
        (
            hold["id"],
            hold["name"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            len(hold["geometry"]),
        )
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert {hold["kind"] for hold in board["holds"]} < FOUNDATION_HOLD_KINDS

    for hold in board["holds"]:
        for piece, expected_frame in zip(
            hold["geometry"], EXPECTED_PIXEL_FRAMES[hold["id"]], strict=True
        ):
            shape = piece["shape"]
            commands = shape["commands"]
            assert shape["type"] == "path"
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            assert commands[1:-1]
            assert all(command["command"] == "curve" for command in commands[1:-1])
            assert 0 <= piece["frame"]["x"] < (
                piece["frame"]["x"] + piece["frame"]["width"]
            ) <= 1
            assert 0 <= piece["frame"]["y"] < (
                piece["frame"]["y"] + piece["frame"]["height"]
            ) <= 1
            assert piece["frame"]["width"] * piece["frame"]["height"] > 0
            for actual, expected in zip(
                (
                    piece["frame"]["x"] * PRESENTATION_SIZE[0],
                    piece["frame"]["y"] * PRESENTATION_SIZE[1],
                    piece["frame"]["width"] * PRESENTATION_SIZE[0],
                    piece["frame"]["height"] * PRESENTATION_SIZE[1],
                ),
                expected_frame,
                strict=True,
            ):
                assert math.isclose(actual, expected, abs_tol=1e-7)
            points = [point for command in commands for point in _points(command)]
            assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
            assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
            assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
            assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)

    for left_id, right_id in (
        ("sloper-left", "sloper-right"),
        ("pinch-left", "pinch-right"),
    ):
        for left, right in zip(
            holds[left_id]["geometry"], holds[right_id]["geometry"], strict=True
        ):
            left_frame = left["frame"]
            right_frame = right["frame"]
            assert math.isclose(
                right_frame["x"],
                1 - left_frame["x"] - left_frame["width"],
                abs_tol=1e-12,
            )
            assert math.isclose(right_frame["y"], left_frame["y"], abs_tol=1e-12)
            assert math.isclose(
                right_frame["width"], left_frame["width"], abs_tol=1e-12
            )
            assert math.isclose(
                right_frame["height"], left_frame["height"], abs_tol=1e-12
            )
            for left_command, right_command in zip(
                left["shape"]["commands"], right["shape"]["commands"], strict=True
            ):
                assert left_command["command"] == right_command["command"]
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                    assert math.isclose(right_y, left_y, abs_tol=1e-12)

    assert len(holds["pinch-left"]["geometry"]) == 2
    assert len(holds["pinch-right"]["geometry"]) == 2
    assert all(
        len(hold["geometry"]) == 1
        for hold in board["holds"]
        if hold["kind"] != "pinch"
    )
    assert holds["top-jug-rail"]["geometry"][0]["treatment"] == {
        "type": "shelf",
        "rimInsetFraction": 0.12,
    }
    assert all(
        piece["treatment"] == {"type": "surface"}
        for hold in board["holds"]
        if hold["kind"] != "jug"
        for piece in hold["geometry"]
    )
    assert holds["sloper-left"]["gripType"] == "sloper"
    assert holds["sloper-right"]["gripType"] == "sloper"
    assert all(
        field not in hold
        for hold in board["holds"]
        for field in ("fingerCapacity", "depthRangeMillimeters", "features")
    )
