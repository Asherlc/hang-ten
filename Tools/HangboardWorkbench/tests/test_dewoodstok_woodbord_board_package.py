from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "dewoodstok-woodbord"
EXPECTED_PIXEL_FRAMES = {
    "top-rim": (24.167, 15.391, 1636.58, 34.857),
    "front-upper-1": (67.0, 72.0, 253.001, 72.0),
    "front-upper-2": (373.999, 71.0, 117.999, 73.0),
    "front-upper-3": (549.001, 72.0, 262.0, 71.0),
    "front-upper-4": (872.999, 72.0, 262.0, 71.0),
    "front-upper-5": (1192.001, 71.0, 117.999, 73.0),
    "front-upper-6": (1364.0, 72.0, 253.001, 72.0),
    "front-middle-1": (67.0, 195.0, 253.001, 71.0),
    "front-middle-2": (373.999, 195.0, 248.0, 71.0),
    "front-middle-3": (1062.001, 195.0, 248.0, 71.0),
    "front-middle-4": (1364.0, 195.0, 253.001, 71.0),
    "front-lower-1": (67.0, 317.0, 253.001, 72.0),
    "front-lower-2": (373.999, 316.0, 117.999, 74.0),
    "front-lower-3": (549.001, 317.0, 263.001, 72.0),
    "front-lower-4": (871.998, 317.0, 263.001, 72.0),
    "front-lower-5": (1192.001, 316.0, 117.999, 74.0),
    "front-lower-6": (1364.0, 317.0, 253.001, 72.0),
}
EXPECTED_HOLDS = (
    "top-rim",
    *(f"front-upper-{index}" for index in range(1, 7)),
    *(f"front-middle-{index}" for index in range(1, 5)),
    *(f"front-lower-{index}" for index in range(1, 7)),
)
MIRRORED_PAIRS = (
    *((f"front-upper-{left}", f"front-upper-{7 - left}") for left in range(1, 4)),
    *((f"front-middle-{left}", f"front-middle-{5 - left}") for left in range(1, 3)),
    *((f"front-lower-{left}", f"front-lower-{7 - left}") for left in range(1, 4)),
)
EXPECTED_FINGER_CAPACITIES = {
    "top-rim": None,
    "front-upper-1": 4,
    "front-upper-2": 2,
    "front-upper-3": 4,
    "front-upper-4": 4,
    "front-upper-5": 2,
    "front-upper-6": 4,
    "front-middle-1": 4,
    "front-middle-2": 4,
    "front-middle-3": 4,
    "front-middle-4": 4,
    "front-lower-1": 4,
    "front-lower-2": 2,
    "front-lower-3": 4,
    "front-lower-4": 4,
    "front-lower-5": 2,
    "front-lower-6": 4,
}
TOP_RIM_COMMAND_SIGNATURE = (
    ("move", (0.048229873043, 0.002568095969), None, None, None),
    ("line", (0.957526152209, 0.054875575786), None, None, None),
    ("curve", (1.0, 1.0), None, (0.980163390459, -0.036360849873), (1.0, 0.586879485543)),
    ("line", (0.0, 0.99128209626), None, None, None),
    ("quad", (0.048229873043, 0.002568095969), (0.008889321398, -0.052303456308), None, None),
    ("close", None, None, None, None),
)
UPPER_WIDE_POCKET_COMMAND_SIGNATURE = (
    ("move", (0.142291187525, 0.0), None, None, None),
    ("line", (0.857708812475, 0.0), None, None, None),
    ("curve", (1.0, 0.5), None, (0.936294066978, 0.0), (1.0, 0.223857619471)),
    ("curve", (0.857708812475, 1.0), None, (1.0, 0.776142380529), (0.936294066978, 1.0)),
    ("line", (0.142291187525, 1.0), None, None, None),
    ("curve", (0.0, 0.5), None, (0.063705933022, 1.0), (0.0, 0.776142380529)),
    ("curve", (0.142291187525, 0.0), None, (0.0, 0.223857619471), (0.063705933022, 0.0)),
    ("close", None, None, None, None),
)
UPPER_NARROW_POCKET_COMMAND_SIGNATURE = (
    ("move", (0.309324072404, 0.0), None, None, None),
    ("line", (0.690675927596, 0.0), None, None, None),
    ("curve", (1.0, 0.5), None, (0.861510895684, 0.0), (1.0, 0.223857624853)),
    ("curve", (0.690675927596, 1.0), None, (1.0, 0.776142375147), (0.861510895684, 1.0)),
    ("line", (0.309324072404, 1.0), None, None, None),
    ("curve", (0.0, 0.5), None, (0.138489104316, 1.0), (0.0, 0.776142375147)),
    ("curve", (0.309324072404, 0.0), None, (0.0, 0.223857624853), (0.138489104316, 0.0)),
    ("close", None, None, None, None),
)
UPPER_CENTER_POCKET_COMMAND_SIGNATURE = (
    ("move", (0.135495874993, 0.0), None, None, None),
    ("line", (0.864504128824, 0.0), None, None, None),
    ("curve", (1.0, 0.500000007042), None, (0.939336432633, 0.0), (1.0, 0.223857620111)),
    ("curve", (0.864504128824, 1.0), None, (1.0, 0.776142379889), (0.939336432633, 1.0)),
    ("line", (0.135495874993, 1.0), None, None, None),
    ("curve", (0.0, 0.500000007042), None, (0.060663567367, 1.0), (0.0, 0.776142379889)),
    ("curve", (0.135495874993, 0.0), None, (0.0, 0.223857620111), (0.060663567367, 0.0)),
    ("close", None, None, None, None),
)
MIDDLE_OUTER_POCKET_COMMAND_SIGNATURE = (
    ("move", (0.140315604714, 0.0), None, None, None),
    ("line", (0.859684399239, 0.0), None, None, None),
    ("curve", (1.0, 0.500000007042), None, (0.937178566213, 0.0), (1.0, 0.223857620111)),
    ("curve", (0.859684399239, 1.0), None, (1.0, 0.776142379889), (0.937178566213, 1.0)),
    ("line", (0.140315604714, 1.0), None, None, None),
    ("curve", (0.0, 0.500000007042), None, (0.062821433787, 1.0), (0.0, 0.776142379889)),
    ("curve", (0.140315604714, 0.0), None, (0.0, 0.223857620111), (0.062821433787, 0.0)),
    ("close", None, None, None, None),
)
MIDDLE_INNER_POCKET_COMMAND_SIGNATURE = (
    ("move", (0.143145062354, 0.0), None, None, None),
    ("line", (0.856854937646, 0.0), None, None, None),
    ("curve", (1.0, 0.500000007042), None, (0.935911774924, 0.0), (1.0, 0.223857620111)),
    ("curve", (0.856854937646, 1.0), None, (1.0, 0.776142379889), (0.935911774924, 1.0)),
    ("line", (0.143145062354, 1.0), None, None, None),
    ("curve", (0.0, 0.500000007042), None, (0.064088225076, 1.0), (0.0, 0.776142379889)),
    ("curve", (0.143145062354, 0.0), None, (0.0, 0.223857620111), (0.064088225076, 0.0)),
    ("close", None, None, None, None),
)
LOWER_NARROW_POCKET_COMMAND_SIGNATURE = (
    ("move", (0.313559899601, 0.0), None, None, None),
    ("line", (0.686440108874, 0.0), None, None, None),
    ("curve", (1.0, 0.500000006757), None, (0.859614453581, 0.0), (1.0, 0.223857624166)),
    ("curve", (0.686440108874, 1.0), None, (1.0, 0.776142375834), (0.859614453581, 1.0)),
    ("line", (0.313559899601, 1.0), None, None, None),
    ("curve", (0.0, 0.500000006757), None, (0.140385546419, 1.0), (0.0, 0.776142375834)),
    ("curve", (0.313559899601, 0.0), None, (0.0, 0.223857624166), (0.140385546419, 0.0)),
    ("close", None, None, None, None),
)
LOWER_CENTER_POCKET_COMMAND_SIGNATURE = (
    ("move", (0.136880872562, 0.0), None, None, None),
    ("line", (0.863119127438, 0.0), None, None, None),
    ("curve", (1.0, 0.5), None, (0.938716347434, 0.0), (1.0, 0.223857619471)),
    ("curve", (0.863119127438, 1.0), None, (1.0, 0.776142380529), (0.938716347434, 1.0)),
    ("line", (0.136880872562, 1.0), None, None, None),
    ("curve", (0.0, 0.5), None, (0.061283652566, 1.0), (0.0, 0.776142380529)),
    ("curve", (0.136880872562, 0.0), None, (0.0, 0.223857619471), (0.061283652566, 0.0)),
    ("close", None, None, None, None),
)
EXPECTED_PATH_SIGNATURES = {
    "top-rim": TOP_RIM_COMMAND_SIGNATURE,
    "front-upper-1": UPPER_WIDE_POCKET_COMMAND_SIGNATURE,
    "front-upper-2": UPPER_NARROW_POCKET_COMMAND_SIGNATURE,
    "front-upper-3": UPPER_CENTER_POCKET_COMMAND_SIGNATURE,
    "front-upper-4": UPPER_CENTER_POCKET_COMMAND_SIGNATURE,
    "front-upper-5": UPPER_NARROW_POCKET_COMMAND_SIGNATURE,
    "front-upper-6": UPPER_WIDE_POCKET_COMMAND_SIGNATURE,
    "front-middle-1": MIDDLE_OUTER_POCKET_COMMAND_SIGNATURE,
    "front-middle-2": MIDDLE_INNER_POCKET_COMMAND_SIGNATURE,
    "front-middle-3": MIDDLE_INNER_POCKET_COMMAND_SIGNATURE,
    "front-middle-4": MIDDLE_OUTER_POCKET_COMMAND_SIGNATURE,
    "front-lower-1": UPPER_WIDE_POCKET_COMMAND_SIGNATURE,
    "front-lower-2": LOWER_NARROW_POCKET_COMMAND_SIGNATURE,
    "front-lower-3": LOWER_CENTER_POCKET_COMMAND_SIGNATURE,
    "front-lower-4": LOWER_CENTER_POCKET_COMMAND_SIGNATURE,
    "front-lower-5": LOWER_NARROW_POCKET_COMMAND_SIGNATURE,
    "front-lower-6": UPPER_WIDE_POCKET_COMMAND_SIGNATURE,
}

sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


def _png_dimensions(image_path: Path) -> tuple[int, int]:
    signature = image_path.read_bytes()[:24]
    assert signature[:8] == b"\x89PNG\r\n\x1a\n"
    assert signature[12:16] == b"IHDR"
    return struct.unpack(">II", signature[16:24])


def _command_signature(hold: dict[str, object]) -> tuple[tuple[object, ...], ...]:
    commands = hold["geometry"][0]["shape"]["commands"]
    return tuple(
        (
            command["command"],
            tuple(command["to"]) if "to" in command else None,
            tuple(command["control"]) if "control" in command else None,
            tuple(command["control1"]) if "control1" in command else None,
            tuple(command["control2"]) if "control2" in command else None,
        )
        for command in commands
    )


def _assert_signature_matches(
    actual: tuple[tuple[object, ...], ...],
    expected: tuple[tuple[object, ...], ...],
) -> None:
    assert len(actual) == len(expected)
    for actual_command, expected_command in zip(actual, expected, strict=True):
        assert actual_command[0] == expected_command[0]
        for actual_value, expected_value in zip(actual_command[1:], expected_command[1:], strict=True):
            if actual_value is None or expected_value is None:
                assert actual_value == expected_value
            else:
                assert actual_value == pytest.approx(expected_value, abs=1e-8)


def _pixel_frame(frame: dict[str, float], size: tuple[int, int]) -> tuple[float, float, float, float]:
    width, height = size
    return (frame["x"] * width, frame["y"] * height, frame["width"] * width, frame["height"] * height)


def test_dewoodstok_woodbord_inventory_geometry_and_symmetry() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}
    image_width, image_height = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")
    image_aspect_ratio = image_width / image_height

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "dewoodstok-woodbord"
    assert board["manufacturer"] == "deWoodstok"
    assert board["name"] == "Woodbord"
    assert board["subtitle"] == "Solid certified bamboo hangboard."
    assert board["productURL"] == "https://www.dewoodstok.nl/product/hangboard-woodbord/"
    assert board["dimensions"] == "590 × 148 × 40 mm"
    assert math.isclose(board["aspectRatio"], image_aspect_ratio, rel_tol=0, abs_tol=1e-12)
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert tuple(hold["id"] for hold in board["holds"]) == EXPECTED_HOLDS
    assert tuple(holds) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in holds.values()) == {"pocket": 16, "jug": 1}
    assert holds["top-rim"]["kind"] == "jug"
    assert all(holds[hold_id]["kind"] == "pocket" for hold_id in EXPECTED_HOLDS[1:])
    assert all("sizeMillimeters" not in hold for hold in holds.values())
    assert all("depthRangeMillimeters" not in hold for hold in holds.values())
    assert all("gripType" not in hold for hold in holds.values())
    assert all("features" not in hold for hold in holds.values())

    crop_translation = None
    for hold in holds.values():
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        commands = piece["shape"]["commands"]
        assert piece["shape"]["type"] == "path"
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert any(command["command"] == "curve" for command in commands)
        assert len(commands) >= 6
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        projected = _pixel_frame(frame, (image_width, image_height))
        expected = EXPECTED_PIXEL_FRAMES[hold["id"]]
        assert projected[2:] == pytest.approx(expected[2:], abs=0.002)
        translation = (projected[0] - expected[0], projected[1] - expected[1])
        if crop_translation is None:
            crop_translation = translation
        else:
            assert translation == pytest.approx(crop_translation, abs=0.01)

    assert crop_translation is not None
    symmetry_axis_x = None
    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]
        right = holds[right_id]
        left_frame = left["geometry"][0]["frame"]
        right_frame = right["geometry"][0]["frame"]
        assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-6)
        assert right_frame["width"] == pytest.approx(left_frame["width"], abs=1e-6)
        assert right_frame["height"] == pytest.approx(left_frame["height"], abs=1e-6)
        _assert_signature_matches(_command_signature(right), _command_signature(left))
        pair_axis_x = (
            left_frame["x"]
            + left_frame["width"]
            + right_frame["x"]
        ) / 2
        if symmetry_axis_x is None:
            symmetry_axis_x = pair_axis_x
        else:
            assert pair_axis_x == pytest.approx(symmetry_axis_x, abs=1e-6)

    assert symmetry_axis_x is not None
    assert 0 < symmetry_axis_x < 1

    capacities = Counter(hold.get("fingerCapacity") for hold in holds.values())
    assert capacities == {4: 12, 2: 4, None: 1}
    assert {hold_id: hold.get("fingerCapacity") for hold_id, hold in holds.items()} == EXPECTED_FINGER_CAPACITIES
    actual_signatures = {hold_id: _command_signature(hold) for hold_id, hold in holds.items()}
    assert actual_signatures.keys() == EXPECTED_PATH_SIGNATURES.keys()
    for hold_id, expected_signature in EXPECTED_PATH_SIGNATURES.items():
        _assert_signature_matches(actual_signatures[hold_id], expected_signature)

    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    for forbidden in (
        "sizeMillimeters",
        "depthRangeMillimeters",
        "gripType",
        "features",
        "cueStyle",
        "shortLabel",
        "detail",
        "semantics",
        "evidence",
        "claims",
        "instructions",
    ):
        assert forbidden not in raw_document
