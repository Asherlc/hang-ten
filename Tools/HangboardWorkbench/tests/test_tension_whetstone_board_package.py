from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "tension-whetstone"
PRESENTATION_SIZE = (1536, 1024)
EXPECTED_PIXEL_FRAMES = {
    "top-jug": (32, 344, 1472, 77.08333333333333),
    "pocket-40-two-left": (61, 420.0416666666667, 107, 140.625),
    "pocket-40-two-right": (1368, 420.0416666666667, 107, 140.625),
    "edge-40-left": (226, 453.375, 185, 53.125),
    "edge-40-right": (962, 453.375, 163, 53.125),
    "edge-30-left": (411, 453.375, 163, 53.125),
    "edge-30-right": (1125, 453.375, 185, 53.125),
    "center-edge-40": (632, 494, 272, 100),
    "edge-25-left": (226, 589.8333333333334, 185, 71.875),
    "edge-25-right": (962, 589.8333333333334, 163, 71.875),
    "edge-20-left": (411, 589.8333333333334, 163, 71.875),
    "edge-20-right": (1125, 589.8333333333334, 185, 71.875),
}

sys.path.insert(0, str(WORKBENCH_ROOT))

from board_package import load_board_package  # noqa: E402


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return struct.unpack(">II", header[16:24])


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)  # type: ignore[arg-type]
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def test_tension_whetstone_audited_inventory_and_contact_symmetry() -> None:
    """Malformed or noncanonical Whetstone package content must be rejected."""
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    presentation_width, presentation_height = _png_dimensions(
        PACKAGE_ROOT / "assets" / "primary.png"
    )
    assert (presentation_width, presentation_height) == PRESENTATION_SIZE

    assert board["id"] == "tension.whetstone"
    assert board["manufacturer"] == "Tension Climbing"
    assert board["name"] == "Whetstone"
    assert board["dimensions"] == "25 × 6 × 2 in"
    assert math.isclose(
        board["aspectRatio"],
        presentation_width / presentation_height,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(holds) == (
        "top-jug",
        "pocket-40-two-left",
        "pocket-40-two-right",
        "edge-40-left",
        "edge-40-right",
        "edge-30-left",
        "edge-30-right",
        "center-edge-40",
        "edge-25-left",
        "edge-25-right",
        "edge-20-left",
        "edge-20-right",
    )
    assert Counter(hold["kind"] for hold in holds.values()) == {
        "edge": 9,
        "pocket": 2,
        "jug": 1,
    }
    assert tuple(
        (hold_id, holds[hold_id]["sizeMillimeters"])
        for hold_id in holds
        if hold_id != "top-jug"
    ) == (
        ("pocket-40-two-left", 40),
        ("pocket-40-two-right", 40),
        ("edge-40-left", 40),
        ("edge-40-right", 40),
        ("edge-30-left", 30),
        ("edge-30-right", 30),
        ("center-edge-40", 40),
        ("edge-25-left", 25),
        ("edge-25-right", 25),
        ("edge-20-left", 20),
        ("edge-20-right", 20),
    )
    assert holds["pocket-40-two-left"]["fingerCapacity"] == 2
    assert holds["pocket-40-two-right"]["fingerCapacity"] == 2
    assert holds["pocket-40-two-left"]["gripType"] == "twoFingerPocket"
    assert holds["pocket-40-two-right"]["gripType"] == "twoFingerPocket"
    assert all(
        "fingerCapacity" not in holds[hold_id] and "gripType" not in holds[hold_id]
        for hold_id in holds
        if hold_id not in {"pocket-40-two-left", "pocket-40-two-right"}
    )
    assert all(len(hold["geometry"]) == 1 for hold in holds.values())

    for hold in holds.values():
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
        expected_frame = EXPECTED_PIXEL_FRAMES[hold["id"]]
        actual_frame = (
            frame["x"] * presentation_width,
            frame["y"] * presentation_height,
            frame["width"] * presentation_width,
            frame["height"] * presentation_height,
        )
        for actual, expected in zip(actual_frame, expected_frame, strict=True):
            assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-8)

        points = tuple(point for command in commands for point in _points(command))
        assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
        assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
        assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
        assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)

    # The asymmetric depth labels are translated across otherwise mirrored zones.
    for left_id, right_id in (
        ("pocket-40-two-left", "pocket-40-two-right"),
        ("edge-40-left", "edge-30-right"),
        ("edge-30-left", "edge-40-right"),
        ("edge-25-left", "edge-20-right"),
        ("edge-20-left", "edge-25-right"),
    ):
        left = holds[left_id]["geometry"][0]
        right = holds[right_id]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]
        assert math.isclose(
            right_frame["x"], 1 - left_frame["x"] - left_frame["width"], abs_tol=1e-12
        )
        assert math.isclose(right_frame["y"], left_frame["y"], abs_tol=1e-12)
        assert math.isclose(right_frame["width"], left_frame["width"], abs_tol=1e-12)
        assert math.isclose(right_frame["height"], left_frame["height"], abs_tol=1e-12)
        for left_command, right_command in zip(
            left["shape"]["commands"], right["shape"]["commands"], strict=True
        ):
            assert left_command["command"] == right_command["command"]
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    top_jug = holds["top-jug"]["geometry"][0]["frame"]
    assert math.isclose(
        top_jug["x"], 1 - top_jug["x"] - top_jug["width"], abs_tol=1e-12
    )
    center = holds["center-edge-40"]["geometry"][0]["frame"]
    assert math.isclose(center["x"], 1 - center["x"] - center["width"], abs_tol=1e-12)

    assert all("depthRangeMillimeters" not in hold for hold in holds.values())
    assert all("features" not in hold for hold in holds.values())
