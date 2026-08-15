from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "zlagboard-evo"
PRIMARY = PACKAGE_ROOT / "assets" / "primary.png"
sys.path.insert(0, str(WORKBENCH_ROOT))

from board_package import load_board_package  # noqa: E402
EXPECTED_HOLDS = (
    ("jug-top-left", "jug", None),
    ("sloper-32-left", "sloper", None),
    ("sloper-20-left", "sloper", None),
    ("jug-sloper-center", "jug", None),
    ("sloper-20-right", "sloper", None),
    ("sloper-32-right", "sloper", None),
    ("jug-top-right", "jug", None),
    ("edge-upper-30-left", "edge", 30),
    ("sloper-upper-30-left", "sloper", 30),
    ("sloper-upper-25-left", "sloper", 25),
    ("edge-upper-35-center", "edge", 35),
    ("sloper-upper-25-right", "sloper", 25),
    ("sloper-upper-30-right", "sloper", 30),
    ("edge-upper-30-right", "edge", 30),
    ("edge-lower-20-left", "edge", 20),
    ("sloper-lower-25-left", "sloper", 25),
    ("pocket-lower-30-left", "pocket", 30),
    ("sloper-lower-30-center", "sloper", 30),
    ("pocket-lower-30-right", "pocket", 30),
    ("sloper-lower-25-right", "sloper", 25),
    ("edge-lower-20-right", "edge", 20),
)
MIRRORED_PAIRS = (
    ("jug-top-left", "jug-top-right"),
    ("sloper-32-left", "sloper-32-right"),
    ("sloper-20-left", "sloper-20-right"),
    ("edge-upper-30-left", "edge-upper-30-right"),
    ("sloper-upper-30-left", "sloper-upper-30-right"),
    ("sloper-upper-25-left", "sloper-upper-25-right"),
    ("edge-lower-20-left", "edge-lower-20-right"),
    ("sloper-lower-25-left", "sloper-lower-25-right"),
    ("pocket-lower-30-left", "pocket-lower-30-right"),
)


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for key, point in command.items()
        if key != "command"
    )


def _assert_exact_global_mirror(
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
    for left_command, right_command in zip(
        left_commands, right_commands, strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def _frame_overlap(first: dict[str, float], second: dict[str, float]) -> float:
    width = max(
        0.0,
        min(first["x"] + first["width"], second["x"] + second["width"])
        - max(first["x"], second["x"]),
    )
    height = max(
        0.0,
        min(first["y"] + first["height"], second["y"] + second["height"])
        - max(first["y"], second["y"]),
    )
    return width * height


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(child) for child in value))
    return set()


def _png_ihdr(path: Path) -> tuple[int, int, int, int, int, int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload[8:12] == struct.pack(">I", 13)
    assert payload[12:16] == b"IHDR"
    return struct.unpack(">IIBBBBB", payload[16:29])


def test_zlagboard_evo_preserves_audited_inventory_geometry_and_asset() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    board_holds = board["holds"]
    assert isinstance(board_holds, list)
    holds = {hold["id"]: hold for hold in board_holds}

    assert board["id"] == "zlagboard.evo"
    assert board["manufacturer"] == "Zlagboard"
    assert board["name"] == "Zlagboard Evo"
    assert board["productURL"] == "https://www.zlagboard.com/hangboards"
    assert board["dimensions"] == "8 × 23 × 70.5 cm"
    assert math.isclose(board["aspectRatio"], 2081 / 755, abs_tol=1e-12)
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }

    assert tuple(
        (hold["id"], hold["kind"], hold.get("sizeMillimeters"))
        for hold in board_holds
    ) == EXPECTED_HOLDS
    assert holds["jug-sloper-center"]["name"] == "Center sloper JUG"
    assert Counter(hold["kind"] for hold in board_holds) == {
        "jug": 3,
        "sloper": 11,
        "edge": 5,
        "pocket": 2,
    }
    assert len(board_holds) == 21
    assert sum(len(hold["geometry"]) for hold in board_holds) == 21

    pieces = []
    for hold in board_holds:
        assert len(hold["geometry"]) == 1
        assert "fingerCapacity" not in hold
        assert "gripType" not in hold
        assert "features" not in hold
        assert "depthRangeMillimeters" not in hold
        piece = hold["geometry"][0]
        pieces.append(piece)
        shape = piece["shape"]
        frame = piece["frame"]
        assert shape["type"] == "path"
        assert shape["commands"][0]["command"] == "move"
        assert shape["commands"][-1]["command"] == "close"
        assert sum(
            command["command"] == "curve" for command in shape["commands"]
        ) >= 4
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0

    assert len({json.dumps(piece, sort_keys=True) for piece in pieces}) == 21
    for index, first in enumerate(pieces):
        for second in pieces[index + 1 :]:
            assert _frame_overlap(first["frame"], second["frame"]) == pytest.approx(
                0.0, abs=1e-12
            )

    for left_id, right_id in MIRRORED_PAIRS:
        _assert_exact_global_mirror(
            holds[left_id]["geometry"][0], holds[right_id]["geometry"][0]
        )
    for center_id in ("edge-upper-35-center", "sloper-lower-30-center"):
        center = holds[center_id]["geometry"][0]["frame"]
        assert center["x"] == pytest.approx(
            1 - center["x"] - center["width"], abs=1e-12
        )

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {
        "cueStyle",
        "shortLabel",
        "semantics",
        "evidence",
        "claims",
        "ui",
        "instructions",
        "fingerCapacity",
        "gripType",
        "features",
        "depthRangeMillimeters",
    }
    assert forbidden.isdisjoint(_keys(raw))

    assert sha256(PRIMARY.read_bytes()).hexdigest() == (
        "a7bb1306f6f234637d6dc480b21ee1a41af8ef3fe3dc0e092160f6eae4054787"
    )
    width, height, bit_depth, color_type, compression, filter_method, interlace = (
        _png_ihdr(PRIMARY)
    )
    assert (width, height) == (2081, 755)
    assert (bit_depth, color_type, compression, filter_method, interlace) == (
        8,
        2,
        0,
        0,
        0,
    )
