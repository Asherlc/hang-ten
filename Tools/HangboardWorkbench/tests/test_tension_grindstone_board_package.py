from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "tension-grindstone"
EXPECTED_HOLDS = (
    ("top-jug", "jug", None, 3),
    ("edge-10-left", "edge", 10, 1),
    ("edge-10-right", "edge", 10, 1),
    ("edge-8-left", "edge", 8, 1),
    ("edge-8-right", "edge", 8, 1),
    ("edge-30-left", "edge", 30, 1),
    ("edge-30-right", "edge", 30, 1),
    ("edge-25-left", "edge", 25, 1),
    ("edge-25-right", "edge", 25, 1),
    ("center-edge-50", "edge", 50, 1),
    ("edge-20-left", "edge", 20, 1),
    ("edge-20-right", "edge", 20, 1),
    ("edge-15-left", "edge", 15, 1),
    ("edge-15-right", "edge", 15, 1),
)
PRESENTATION_SIZE = (1672, 941)
EXPECTED_PIXEL_FRAMES = {
    ("top-jug", 0): (31.768, 253.129, 745.712, 26.348),
    ("top-jug", 1): (894.52, 253.129, 745.712, 26.348),
    ("top-jug", 2): (760.76, 265.362, 150.48, 30.112),
    ("edge-10-left", 0): (87.78, 290.769, 278.388, 60.224),
    ("edge-10-right", 0): (1045.0, 290.769, 260.832, 60.224),
    ("edge-8-left", 0): (366.168, 290.769, 260.832, 60.224),
    ("edge-8-right", 0): (1305.832, 290.769, 278.388, 60.224),
    ("edge-30-left", 0): (90.288, 430.978, 299.288, 77.162),
    ("edge-30-right", 0): (1026.608, 430.978, 255.816, 77.162),
    ("edge-25-left", 0): (389.576, 430.978, 255.816, 77.162),
    ("edge-25-right", 0): (1282.424, 430.978, 299.288, 77.162),
    ("center-edge-50", 0): (703.912, 497.789, 264.176, 22.13232),
    ("edge-20-left", 0): (112.024, 572.128, 282.568, 79.044),
    ("edge-20-right", 0): (1024.936, 572.128, 252.472, 79.044),
    ("edge-15-left", 0): (394.592, 572.128, 252.472, 79.044),
    ("edge-15-right", 0): (1277.408, 572.128, 282.568, 79.044),
}
ALLOWED_HOLD_KINDS = {"jug", "edge", "pocket", "pinch", "sloper"}
REVIEWED_CENTER_EDGE_50 = {
    "frame": {"x": 0.421, "y": 0.529, "width": 0.158, "height": 0.024},
    "shape": {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0.08, 0.02]},
            {
                "command": "curve",
                "control1": [0.28, 0],
                "control2": [0.4, 0.05],
                "to": [0.5, 0.09],
            },
            {
                "command": "curve",
                "control1": [0.6, 0.05],
                "control2": [0.72, 0],
                "to": [0.92, 0.02],
            },
            {
                "command": "curve",
                "control1": [0.98, 0.1],
                "control2": [1, 0.3],
                "to": [1, 0.5],
            },
            {
                "command": "curve",
                "control1": [1, 0.76],
                "control2": [0.97, 0.93],
                "to": [0.9, 0.98],
            },
            {
                "command": "curve",
                "control1": [0.67, 0.93],
                "control2": [0.33, 0.93],
                "to": [0.1, 0.98],
            },
            {
                "command": "curve",
                "control1": [0.03, 0.93],
                "control2": [0, 0.76],
                "to": [0, 0.5],
            },
            {
                "command": "curve",
                "control1": [0, 0.3],
                "control2": [0.02, 0.1],
                "to": [0.08, 0.02],
            },
            {"command": "close"},
        ],
    },
}

sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
import board_geometry  # noqa: E402


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _absolute_renderer_commands(
    piece: dict[str, object], *, label: str
) -> list[tuple[str, tuple[float, ...]]]:
    frame = piece["frame"]
    shape = piece["shape"]
    assert isinstance(frame, dict)
    assert isinstance(shape, dict)
    commands = shape["commands"]
    assert isinstance(commands, list)
    return board_geometry._shape_commands(
        board_geometry.NormalizedFrame.from_json(frame, f"{label}.frame"),
        commands,
        *PRESENTATION_SIZE,
        label=label,
    )


def _assert_piece_is_exact_global_mirror(
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


def test_tension_grindstone_aspect_ratio_matches_presentation_header() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    presentation_size = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")

    assert math.isclose(
        board["aspectRatio"],
        presentation_size[0] / presentation_size[1],
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def test_tension_grindstone_preserves_audited_asymmetric_depth_zones() -> None:
    presentation_size = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {entry.name for entry in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {entry.name for entry in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert presentation_size == PRESENTATION_SIZE
    assert board["id"] == "tension.grindstone"
    assert board["manufacturer"] == "Tension Climbing"
    assert board["name"] == "Grindstone"
    assert board["dimensions"] == "22 × 6 × 2.75 in"
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(
        (hold["id"], hold["kind"], hold.get("sizeMillimeters"), len(hold["geometry"]))
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert all(hold["kind"] in ALLOWED_HOLD_KINDS for hold in board["holds"])
    assert Counter(hold["kind"] for hold in board["holds"]) == Counter(
        {"edge": 13, "jug": 1}
    )
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 16

    visited_frame_keys = set()
    for hold in board["holds"]:
        for piece_index, piece in enumerate(hold["geometry"]):
            shape = piece["shape"]
            frame = piece["frame"]
            assert isinstance(shape, dict)
            assert isinstance(frame, dict)
            assert shape["type"] == "path"
            commands = shape["commands"]
            assert isinstance(commands, list)
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            assert all(
                command["command"] in {"move", "curve", "close"}
                for command in commands
            )
            assert sum(command["command"] == "curve" for command in commands) >= 4
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            assert frame["width"] * frame["height"] > 0

            points = [point for command in commands for point in _points(command)]
            assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
            assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
            assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
            assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)

            frame_key = (hold["id"], piece_index)
            visited_frame_keys.add(frame_key)
            actual_pixel_frame = (
                frame["x"] * presentation_size[0],
                frame["y"] * presentation_size[1],
                frame["width"] * presentation_size[0],
                frame["height"] * presentation_size[1],
            )
            for actual, expected in zip(
                actual_pixel_frame, EXPECTED_PIXEL_FRAMES[frame_key], strict=True
            ):
                assert math.isclose(actual, expected, abs_tol=1e-6)
    assert visited_frame_keys == set(EXPECTED_PIXEL_FRAMES)

    top_jug = holds["top-jug"]
    _assert_piece_is_exact_global_mirror(top_jug["geometry"][0], top_jug["geometry"][1])
    bridge_frame = top_jug["geometry"][2]["frame"]
    assert bridge_frame["x"] == pytest.approx(
        1 - bridge_frame["x"] - bridge_frame["width"], abs=1e-12
    )

    # Compare the foundation renderer's raw, pre-SVG-format coordinates so
    # this guard cannot hide a ULP difference through text serialization.
    center_edge = holds["center-edge-50"]["geometry"][0]
    reviewed_commands = _absolute_renderer_commands(
        REVIEWED_CENTER_EDGE_50, label="reviewed center-edge-50"
    )
    canonical_commands = _absolute_renderer_commands(
        center_edge, label="canonical center-edge-50"
    )
    assert [command for command, _ in canonical_commands] == [
        command for command, _ in reviewed_commands
    ]
    assert canonical_commands == reviewed_commands

    # The routed cavities are physically mirrored, but the depth labels are
    # intentionally asymmetric. A same-ID mirror would attach the wrong depth.
    for left_id, right_id in (
        ("edge-10-left", "edge-8-right"),
        ("edge-8-left", "edge-10-right"),
        ("edge-30-left", "edge-25-right"),
        ("edge-25-left", "edge-30-right"),
        ("edge-20-left", "edge-15-right"),
        ("edge-15-left", "edge-20-right"),
    ):
        _assert_piece_is_exact_global_mirror(
            holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]
        )

    for same_depth_left, same_depth_right in (
        ("edge-10-left", "edge-10-right"),
        ("edge-8-left", "edge-8-right"),
        ("edge-30-left", "edge-30-right"),
        ("edge-25-left", "edge-25-right"),
        ("edge-20-left", "edge-20-right"),
        ("edge-15-left", "edge-15-right"),
    ):
        assert package.hold_frame(same_depth_left).x < 0.5
        assert package.hold_frame(same_depth_right).x > 0.5

    for left_id, right_id in (
        ("edge-10-left", "edge-8-left"),
        ("edge-10-right", "edge-8-right"),
        ("edge-30-left", "edge-25-left"),
        ("edge-30-right", "edge-25-right"),
        ("edge-20-left", "edge-15-left"),
        ("edge-20-right", "edge-15-right"),
    ):
        left, right = sorted(
            (holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]),
            key=lambda piece: piece["frame"]["x"],
        )
        left_frame = left["frame"]
        right_frame = right["frame"]
        assert left_frame["x"] + left_frame["width"] == pytest.approx(
            right_frame["x"], abs=1e-12
        )
        assert left_frame["y"] == pytest.approx(right_frame["y"], abs=1e-12)
        assert left_frame["height"] == pytest.approx(right_frame["height"], abs=1e-12)

    assert all("gripType" not in hold for hold in board["holds"])
    assert all("fingerCapacity" not in hold for hold in board["holds"])
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])
    assert all("features" not in hold for hold in board["holds"])
