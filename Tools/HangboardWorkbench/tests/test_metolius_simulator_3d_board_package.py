from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import struct
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-simulator-3d"
sys.path.insert(0, str(WORKBENCH_ROOT))

from board_package import load_board_package  # noqa: E402


EXPECTED_HOLDS = (
    "jug-outer-left", "jug-outer-right", "sloper-flat-55-left",
    "sloper-flat-55-right", "sloper-round-65-left", "sloper-round-65-right",
    "pocket-30-three-left", "pocket-30-three-right", "edge-25-left",
    "edge-25-right", "edge-19-left", "edge-19-right", "edge-36-left",
    "edge-36-right", "pocket-15-three-left", "pocket-15-three-right",
    "pocket-35-three-left", "pocket-35-three-right", "pocket-17-three-left",
    "pocket-17-three-right", "edge-14-left", "edge-14-right",
    "pocket-30-two-left", "pocket-30-two-right", "pocket-14-two-left",
    "pocket-14-two-right", "jug-center", "pocket-50-three-center",
    "pocket-37-three-center", "pocket-28-two-center", "pocket-32-two-center",
)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index], EXPECTED_HOLDS[index + 1])
    for index in range(0, 26, 2)
)
SURFACE_HOLDS = {
    "jug-outer-left", "jug-outer-right", "sloper-flat-55-left",
    "sloper-flat-55-right", "sloper-round-65-left", "sloper-round-65-right",
    "jug-center",
}
EXPECTED_SIZES = {
    "sloper-flat-55-left": 55, "sloper-flat-55-right": 55,
    "sloper-round-65-left": 65, "sloper-round-65-right": 65,
    "pocket-30-three-left": 30, "pocket-30-three-right": 30,
    "edge-25-left": 25, "edge-25-right": 25, "edge-19-left": 19,
    "edge-19-right": 19, "edge-36-left": 36, "edge-36-right": 36,
    "pocket-15-three-left": 15, "pocket-15-three-right": 15,
    "pocket-35-three-left": 35, "pocket-35-three-right": 35,
    "pocket-17-three-left": 17, "pocket-17-three-right": 17,
    "edge-14-left": 14, "edge-14-right": 14,
    "pocket-30-two-left": 30, "pocket-30-two-right": 30,
    "pocket-14-two-left": 14, "pocket-14-two-right": 14,
    "pocket-50-three-center": 50, "pocket-37-three-center": 37,
    "pocket-28-two-center": 28, "pocket-32-two-center": 32,
}
EXPECTED_PIXEL_FRAMES = {
    "jug-outer-left": (33, 278, 220, 93),
    "jug-outer-right": (1361, 278, 220, 93),
    "sloper-flat-55-left": (253, 258, 235, 110),
    "sloper-flat-55-right": (1126, 258, 235, 110),
    "sloper-round-65-left": (488, 238, 211, 130),
    "sloper-round-65-right": (915, 238, 211, 130),
    "pocket-30-three-left": (85.5, 357, 120, 57),
    "pocket-30-three-right": (1408.5, 357, 120, 57),
    "edge-25-left": (128, 422, 184, 75), "edge-25-right": (1302, 422, 184, 75),
    "edge-19-left": (330, 392, 174, 66), "edge-19-right": (1110, 392, 174, 66),
    "edge-36-left": (523, 377, 168, 60), "edge-36-right": (923, 377, 168, 60),
    "pocket-15-three-left": (202, 521, 143, 65),
    "pocket-15-three-right": (1269, 521, 143, 65),
    "pocket-35-three-left": (381, 494, 143, 61),
    "pocket-35-three-right": (1090, 494, 143, 61),
    "pocket-17-three-left": (562, 482, 132, 52),
    "pocket-17-three-right": (920, 482, 132, 52),
    "edge-14-left": (281, 598, 180, 63), "edge-14-right": (1153, 598, 180, 63),
    "pocket-30-two-left": (499, 579, 85, 52),
    "pocket-30-two-right": (1030, 579, 85, 52),
    "pocket-14-two-left": (621, 572, 83, 49),
    "pocket-14-two-right": (910, 572, 83, 49),
    "jug-center": (699, 176, 216, 116),
    "pocket-50-three-center": (743.5, 290, 127, 52),
    "pocket-37-three-center": (746.5, 395, 121, 51),
    "pocket-28-two-center": (751.5, 494, 111, 47),
    "pocket-32-two-center": (760, 589, 94, 46),
}


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for field in ("to", "control", "control1", "control2")
        if (point := command.get(field)) is not None
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        assert image.read(8) == b"\x89PNG\r\n\x1a\n"
        assert image.read(4) == b"\x00\x00\x00\r"
        assert image.read(4) == b"IHDR"
        return struct.unpack(">II", image.read(8))


def test_metolius_simulator_3d_audited_inventory_and_geometry() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    presentation_size = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "metolius.simulator-3d"
    assert board["manufacturer"] == "Metolius"
    assert board["name"] == "Simulator 3D"
    assert board["dimensions"] == "28 × 8.75 in (711 × 222 mm)"
    assert board["aspectRatio"] == 1.65538461538462
    assert math.isclose(
        board["aspectRatio"],
        presentation_size[0] / presentation_size[1],
        rel_tol=0.001,
    )
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert presentation_size == (1614, 975)
    assert tuple(holds) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in holds.values()) == {
        "pocket": 16, "edge": 8, "sloper": 4, "jug": 3,
    }

    assert {hold_id: holds[hold_id]["sizeMillimeters"] for hold_id in EXPECTED_SIZES} == EXPECTED_SIZES
    assert all("sizeMillimeters" not in holds[hold_id] for hold_id in (
        "jug-outer-left", "jug-outer-right", "jug-center",
    ))
    assert all(holds[hold_id]["fingerCapacity"] == 3 for hold_id in holds if "three" in hold_id)
    assert all(holds[hold_id]["fingerCapacity"] == 2 for hold_id in holds if "two" in hold_id)
    assert all("fingerCapacity" not in holds[hold_id] for hold_id in holds if "three" not in hold_id and "two" not in hold_id)

    for hold_id, hold in holds.items():
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        shape = piece["shape"]
        commands = shape["commands"]
        frame = piece["frame"]
        assert shape["type"] == "path"
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert any(command["command"] == "curve" for command in commands)
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        if hold_id in SURFACE_HOLDS:
            assert piece["treatment"] == {"type": "surface"}
        else:
            assert piece["treatment"]["type"] == "recess"
            assert piece["treatment"]["depth"] in {"deep", "shallow"}

        expected_x, expected_y, expected_width, expected_height = EXPECTED_PIXEL_FRAMES[hold_id]
        assert math.isclose(frame["x"] * presentation_size[0], expected_x, abs_tol=1e-8)
        assert math.isclose(frame["y"] * presentation_size[1], expected_y, abs_tol=1e-8)
        assert math.isclose(frame["width"] * presentation_size[0], expected_width, abs_tol=1e-8)
        assert math.isclose(frame["height"] * presentation_size[1], expected_height, abs_tol=1e-8)

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]["geometry"][0]
        right = holds[right_id]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]
        assert math.isclose(right_frame["x"], 1 - left_frame["x"] - left_frame["width"], abs_tol=1e-12)
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

    for hold_id in (
        "jug-center", "pocket-50-three-center", "pocket-37-three-center",
        "pocket-28-two-center", "pocket-32-two-center",
    ):
        frame = holds[hold_id]["geometry"][0]["frame"]
        assert math.isclose(frame["x"] + frame["width"] / 2, 0.5, abs_tol=0.004)

    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    for forbidden in (
        "cueStyle", "evidence", "claims", "shortLabel", "detail",
        "artwork.json", "semantics.json", "catalog.json",
    ):
        assert forbidden not in raw_document
