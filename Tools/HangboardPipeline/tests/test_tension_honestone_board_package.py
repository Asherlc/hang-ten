from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "tension-honestone"
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


EXPECTED_HOLDS = (
    ("sloper-35-left", "sloper", None),
    ("sloper-35-right", "sloper", None),
    ("sloper-45-left", "sloper", None),
    ("sloper-45-right", "sloper", None),
    ("pocket-25-one-left", "pocket", 25),
    ("pocket-25-one-right", "pocket", 25),
    ("edge-20-left", "edge", 20),
    ("edge-20-right", "edge", 20),
    ("edge-15-left", "edge", 15),
    ("edge-15-right", "edge", 15),
    ("center-edge-25", "edge", 25),
    ("edge-10-left", "edge", 10),
    ("edge-10-right", "edge", 10),
    ("edge-8-left", "edge", 8),
    ("edge-8-right", "edge", 8),
)
EXPECTED_FULL_CANVAS_BOUNDS = {
    "sloper-35-left": (60, 323, 478, 380),
    "sloper-35-right": (874, 324, 1272, 380),
    "sloper-45-left": (478, 290, 874, 380),
    "sloper-45-right": (1272, 291, 1612, 380),
    "pocket-25-one-left": (45, 404, 135, 536),
    "pocket-25-one-right": (1537, 404, 1627, 536),
    "edge-20-left": (202, 423, 420, 481),
    "edge-20-right": (1058, 423, 1252, 481),
    "edge-15-left": (420, 423, 614, 481),
    "edge-15-right": (1252, 423, 1470, 481),
    "center-edge-25": (696, 473, 976, 521),
    "edge-10-left": (202, 543, 423, 601),
    "edge-10-right": (1057, 543, 1249, 601),
    "edge-8-left": (423, 543, 615, 601),
    "edge-8-right": (1249, 543, 1470, 601),
}


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


def _primary_image_dimensions() -> tuple[int, int]:
    header = (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()[:24]

    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"

    return struct.unpack(">II", header[16:24])


def _assert_exact_global_mirror(
    left: dict[str, object], right: dict[str, object]
) -> None:
    left_frame = left["frame"]
    right_frame = right["frame"]
    assert right_frame["x"] == pytest.approx(
        1 - left_frame["x"] - left_frame["width"], abs=1e-12
    )
    assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-12)
    assert right_frame["width"] == pytest.approx(left_frame["width"], abs=1e-12)
    assert right_frame["height"] == pytest.approx(left_frame["height"], abs=1e-12)
    assert right.get("treatment") == left.get("treatment")
    assert [command["command"] for command in right["shape"]["commands"]] == [
        command["command"] for command in left["shape"]["commands"]
    ]
    for left_command, right_command in zip(
        left["shape"]["commands"], right["shape"]["commands"], strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def test_tension_honestone_geometry_uses_the_full_primary_canvas() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    width, height = _primary_image_dimensions()

    assert (width, height) == (1672, 941)
    assert math.isclose(
        board["aspectRatio"], width / height, rel_tol=0, abs_tol=1e-12
    )

    actual_bounds = {
        hold_id: (
            round(piece["frame"]["x"] * width),
            round(piece["frame"]["y"] * height),
            round((piece["frame"]["x"] + piece["frame"]["width"]) * width),
            round((piece["frame"]["y"] + piece["frame"]["height"]) * height),
        )
        for hold_id, hold in holds.items()
        for piece in hold["geometry"]
    }

    assert actual_bounds == EXPECTED_FULL_CANVAS_BOUNDS


def test_tension_honestone_preserves_audited_contacts_and_asymmetric_zones() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}
    width, height = _primary_image_dimensions()

    assert board["id"] == "tension.honestone"
    assert board["manufacturer"] == "Tension Climbing"
    assert board["name"] == "Honestone"
    assert board["dimensions"] == "25 × 6 × 2.5 in"
    assert (width, height) == (1672, 941)
    assert math.isclose(
        board["aspectRatio"], width / height, rel_tol=0, abs_tol=1e-12
    )
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(
        (hold["id"], hold["kind"], hold.get("sizeMillimeters"))
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "sloper": 4,
        "pocket": 2,
        "edge": 9,
    }

    for hold in board["holds"]:
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        assert piece["shape"]["type"] == "path"
        assert piece["shape"]["commands"][0]["command"] == "move"
        assert piece["shape"]["commands"][-1]["command"] == "close"
        assert any(
            command["command"] == "curve" for command in piece["shape"]["commands"]
        )
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0

    # The routed cavities are mirrored, while labels move between inner and
    # outer zones to preserve the manufacturer's consistent grip spacing.
    for left_id, right_id in (
        ("pocket-25-one-left", "pocket-25-one-right"),
        ("edge-20-left", "edge-15-right"),
        ("edge-15-left", "edge-20-right"),
        ("edge-10-left", "edge-8-right"),
        ("edge-8-left", "edge-10-right"),
    ):
        _assert_exact_global_mirror(
            holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]
        )

    # Adjacent depth regions meet at the source-visible shallow step and never
    # swallow the neighbouring region in the same routed slot.
    for outer_id, inner_id in (
        ("edge-20-left", "edge-15-left"),
        ("edge-20-right", "edge-15-right"),
        ("edge-10-left", "edge-8-left"),
        ("edge-10-right", "edge-8-right"),
    ):
        outer = holds[outer_id]["geometry"][0]["frame"]
        inner = holds[inner_id]["geometry"][0]["frame"]
        left, right = sorted((outer, inner), key=lambda frame: frame["x"])
        assert left["x"] + left["width"] == pytest.approx(right["x"], abs=1e-12)
        assert left["y"] == pytest.approx(right["y"], abs=1e-12)
        assert left["height"] == pytest.approx(right["height"], abs=1e-12)

    # The sloper IDs follow the engraved asymmetric 35°/45° sequence:
    # low outer, raised inner, low inner, raised outer.
    assert (
        holds["sloper-35-left"]["geometry"][0]["frame"]["x"]
        < holds["sloper-45-left"]["geometry"][0]["frame"]["x"]
        < 0.5
    )
    assert (
        0.5
        < holds["sloper-35-right"]["geometry"][0]["frame"]["x"]
        < holds["sloper-45-right"]["geometry"][0]["frame"]["x"]
    )
    assert (
        holds["sloper-45-left"]["geometry"][0]["frame"]["y"]
        < holds["sloper-35-left"]["geometry"][0]["frame"]["y"]
    )
    assert (
        holds["sloper-45-right"]["geometry"][0]["frame"]["y"]
        < holds["sloper-35-right"]["geometry"][0]["frame"]["y"]
    )
    assert all(
        holds[hold_id].get("gripType") == "sloper"
        for hold_id in (
            "sloper-35-left",
            "sloper-35-right",
            "sloper-45-left",
            "sloper-45-right",
        )
    )
    assert holds["pocket-25-one-left"].get("fingerCapacity") == 1
    assert holds["pocket-25-one-right"].get("fingerCapacity") == 1
    assert holds["pocket-25-one-left"].get("gripType") is None
    assert holds["pocket-25-one-right"].get("gripType") is None
    assert all(hold.get("depthRangeMillimeters") is None for hold in board["holds"])
    assert all(hold.get("features") is None for hold in board["holds"])

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    forbidden_keys = {"cueStyle", "semantics", "evidence", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(raw_document))
