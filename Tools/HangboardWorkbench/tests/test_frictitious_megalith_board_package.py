from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "frictitious-megalith"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


EXPECTED_PRIMARY_SHA256 = (
    "0d42b04da7413110bc3825060371e4bcad8c3720964cd45532d5b6b458815d49"
)
EXPECTED_HOLDS = (
    ("top-jug", "Full-width pull-up jug", "jug", None, None, 2),
    ("edge-8-left", "Left 8 mm edge", "edge", 8, None, 1),
    ("edge-8-right", "Right 8 mm edge", "edge", 8, None, 1),
    ("edge-10-left", "Left 10 mm edge", "edge", 10, None, 1),
    ("edge-10-right", "Right 10 mm edge", "edge", 10, None, 1),
    ("edge-12-left", "Left 12 mm edge", "edge", 12, None, 1),
    ("edge-12-right", "Right 12 mm edge", "edge", 12, None, 1),
    ("edge-30-left", "Left 30 mm edge", "edge", 30, None, 1),
    ("edge-30-right", "Right 30 mm edge", "edge", 30, None, 1),
    ("edge-40-left", "Left 40 mm edge", "edge", 40, None, 1),
    ("edge-40-right", "Right 40 mm edge", "edge", 40, None, 1),
    (
        "pocket-two-finger-left",
        "Left two-finger pocket",
        "pocket",
        40,
        2,
        1,
    ),
    (
        "pocket-two-finger-right",
        "Right two-finger pocket",
        "pocket",
        40,
        2,
        1,
    ),
    ("edge-15-left", "Left 15 mm edge", "edge", 15, None, 1),
    ("edge-15-right", "Right 15 mm edge", "edge", 15, None, 1),
    ("edge-20-left", "Left 20 mm edge", "edge", 20, None, 1),
    ("edge-20-right", "Right 20 mm edge", "edge", 20, None, 1),
    ("pocket-mono-left", "Left mono pocket", "pocket", None, 1, 1),
    ("pocket-mono-right", "Right mono pocket", "pocket", None, 1, 1),
    ("edge-25-center", "Center 25 mm incut edge", "edge", 25, None, 1),
)
REPEATED_PAIRS = (
    ("edge-8-left", "edge-8-right"),
    ("edge-10-left", "edge-10-right"),
    ("edge-12-left", "edge-12-right"),
    ("edge-30-left", "edge-30-right"),
    ("edge-40-left", "edge-40-right"),
    ("pocket-two-finger-left", "pocket-two-finger-right"),
    ("edge-15-left", "edge-15-right"),
    ("edge-20-left", "edge-20-right"),
    ("pocket-mono-left", "pocket-mono-right"),
)


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key, point in command.items()
        if key != "command"
    )


def _assert_piece_is_exact_global_mirror(
    left: dict[str, object], right: dict[str, object]
) -> None:
    left_frame = left["frame"]
    right_frame = right["frame"]
    left_shape = left["shape"]
    right_shape = right["shape"]
    assert isinstance(left_frame, dict) and isinstance(right_frame, dict)
    assert isinstance(left_shape, dict) and isinstance(right_shape, dict)
    assert right_frame["x"] == pytest.approx(
        1 - left_frame["x"] - left_frame["width"], abs=1e-12
    )
    assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-12)
    assert right_frame["width"] == pytest.approx(left_frame["width"], abs=1e-12)
    assert right_frame["height"] == pytest.approx(left_frame["height"], abs=1e-12)
    assert right.get("treatment") == left.get("treatment")
    assert [command["command"] for command in right_shape["commands"]] == [
        command["command"] for command in left_shape["commands"]
    ]
    for left_command, right_command in zip(
        left_shape["commands"], right_shape["commands"], strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def _assert_piece_repeats_normalized_shape(
    left: dict[str, object], right: dict[str, object]
) -> None:
    left_frame = left["frame"]
    right_frame = right["frame"]
    left_shape = left["shape"]
    right_shape = right["shape"]
    assert isinstance(left_frame, dict) and isinstance(right_frame, dict)
    assert isinstance(left_shape, dict) and isinstance(right_shape, dict)
    assert [command["command"] for command in right_shape["commands"]] == [
        command["command"] for command in left_shape["commands"]
    ]
    for left_command, right_command in zip(
        left_shape["commands"], right_shape["commands"], strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)
    assert left_frame["x"] < 0.5 < right_frame["x"]
    assert right_frame["y"] == pytest.approx(left_frame["y"], abs=0.012)
    assert right_frame["height"] == pytest.approx(left_frame["height"], abs=0.012)


# Mutation caught: changing product identity, source-supported physical facts,
# hold order, hold classification, size/capacity, or physical piece count.
def test_frictitious_megalith_preserves_audited_inventory_and_facts() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    primary = (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()

    assert board["id"] == "frictitious.megalith"
    assert board["manufacturer"] == "Frictitious Climbing"
    assert board["name"] == "Megalith"
    assert board["subtitle"] == (
        "Shoulder-width edges, pockets, center hold, and pull-up jug."
    )
    assert board["productURL"] == (
        "https://frictitiousclimbing.com/products/megalith"
    )
    assert board["dimensions"] == "26.75 × 6.5 × 2.25 in"
    assert primary[:8] == b"\x89PNG\r\n\x1a\n"
    assert primary[12:16] == b"IHDR"
    width, height = struct.unpack(">II", primary[16:24])
    assert (width, height) == (1536, 1024)
    assert board["aspectRatio"] == width / height == 1.5
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert tuple(
        (
            hold["id"],
            hold["name"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
            len(hold["geometry"]),
        )
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert {hold["kind"] for hold in board["holds"]} <= {
        "jug", "edge", "pocket", "pinch", "sloper"
    }
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "edge": 15,
        "pocket": 4,
        "jug": 1,
    }
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 21


# Mutation caught: replacing an audited path with a box/line, opening a path,
# moving geometry outside the presentation, or changing a paired contour into
# an unrelated shape. The calibrated image establishes repeated, not globally
# mirrored, zone placement within the left and right modules.
def test_frictitious_megalith_paths_are_smooth_normalized_and_paired() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    for hold in board["holds"]:
        for piece in hold["geometry"]:
            frame = piece["frame"]
            shape = piece["shape"]
            assert isinstance(frame, dict) and isinstance(shape, dict)
            commands = shape["commands"]
            assert shape["type"] == "path"
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            assert sum(
                command["command"] == "curve" for command in commands
            ) >= 4
            assert {command["command"] for command in commands} <= {
                "move",
                "curve",
                "close",
            }
            for command in commands:
                for x, y in _points(command):
                    assert 0 <= x <= 1
                    assert 0 <= y <= 1
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            assert frame["width"] * frame["height"] > 0

    _assert_piece_is_exact_global_mirror(
        holds["top-jug"]["geometry"][0], holds["top-jug"]["geometry"][1]
    )
    for left_id, right_id in REPEATED_PAIRS:
        _assert_piece_repeats_normalized_shape(
            holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]
        )

    for prefix_group in (
        ("edge-8", "edge-10", "edge-12"),
        ("edge-30", "edge-40"),
        ("edge-15", "edge-20"),
    ):
        for side in ("left", "right"):
            assert [
                holds[f"{prefix}-{side}"]["geometry"][0]["frame"]["x"]
                for prefix in prefix_group
            ] == sorted(
                holds[f"{prefix}-{side}"]["geometry"][0]["frame"]["x"]
                for prefix in prefix_group
            )

    center = holds["edge-25-center"]["geometry"][0]["frame"]
    assert center["x"] + center["width"] / 2 == pytest.approx(0.5, abs=0.005)


# Mutation caught: adding sidecars or unsupported metadata, replacing the
# calibrated primary asset, or attaching inferred grip/depth/feature claims.
def test_frictitious_megalith_package_is_minimal_and_omits_unsupported_claims() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    document = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert hashlib.sha256(
        (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()
    ).hexdigest() == EXPECTED_PRIMARY_SHA256
    assert set(document) == {
        "schemaVersion",
        "id",
        "manufacturer",
        "name",
        "subtitle",
        "productURL",
        "dimensions",
        "aspectRatio",
        "presentation",
        "holds",
    }
    assert all(
        set(raw_hold)
        <= {"id", "name", "kind", "sizeMillimeters", "fingerCapacity", "geometry"}
        for raw_hold in document["holds"]
    )
    assert all(
        set(piece) == {"frame", "shape"}
        for raw_hold in document["holds"]
        for piece in raw_hold["geometry"]
    )
    assert all("gripType" not in hold for hold in board["holds"])
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])
    assert all("features" not in hold for hold in board["holds"])
