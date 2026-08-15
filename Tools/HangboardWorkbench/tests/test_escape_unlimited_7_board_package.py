from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "escape-unlimited-7"
EXPECTED_HOLDS = (
    ("top-sloper-60", "sloper", 60),
    ("edge-45-left", "edge", 45),
    ("edge-45-right", "edge", 45),
    ("edge-20-left", "edge", 20),
    ("edge-20-right", "edge", 20),
    ("edge-15-left", "edge", 15),
    ("edge-15-right", "edge", 15),
)
MIRRORED_PAIRS = (
    ("edge-45-left", "edge-45-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-15-left", "edge-15-right"),
)

sys.path.insert(0, str(WORKBENCH_ROOT))

from board_package import load_board_package  # noqa: E402


def test_escape_unlimited_7_aspect_ratio_matches_png_ihdr() -> None:
    png_header = (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()[:24]

    assert png_header[:8] == b"\x89PNG\r\n\x1a\n"
    assert png_header[12:16] == b"IHDR"
    width, height = struct.unpack(">II", png_header[16:24])
    assert (width, height) == (1774, 887)

    board = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    assert board["aspectRatio"] == width / height


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)  # type: ignore[arg-type]
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def test_escape_unlimited_7_preserves_audited_inventory_and_mirrored_edges() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert board["id"] == "escape-unlimited-7"
    assert board["manufacturer"] == "Escape Climbing"
    assert board["name"] == "Unlimited Board"
    assert board["dimensions"] == "23.75 × 7.25 × 1.875 in"
    assert board["aspectRatio"] == 1774 / 887
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(
        (hold["id"], hold["kind"], hold.get("sizeMillimeters"))
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {"edge": 6, "sloper": 1}

    for hold in board["holds"]:
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        assert piece["shape"]["type"] == "path"
        assert piece["shape"]["commands"][0]["command"] == "move"
        assert piece["shape"]["commands"][-1]["command"] == "close"
        assert len(piece["shape"]["commands"]) >= 8
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        assert "treatment" not in piece
        assert "depthRangeMillimeters" not in hold
        assert "gripType" not in hold
        assert "fingerCapacity" not in hold
        assert "features" not in hold

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]["geometry"][0]
        right = holds[right_id]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]
        assert right_frame["x"] == pytest.approx(
            1 - left_frame["x"] - left_frame["width"]
        )
        assert right_frame["y"] == pytest.approx(left_frame["y"])
        assert right_frame["width"] == pytest.approx(left_frame["width"])
        assert right_frame["height"] == pytest.approx(left_frame["height"])
        assert [command["command"] for command in right["shape"]["commands"]] == [
            command["command"] for command in left["shape"]["commands"]
        ]
        for left_command, right_command in zip(
            left["shape"]["commands"], right["shape"]["commands"], strict=True
        ):
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert right_x == pytest.approx(1 - left_x)
                assert right_y == pytest.approx(left_y)

    crown = holds["top-sloper-60"]["geometry"][0]
    crown_frame = crown["frame"]
    assert crown_frame["x"] == pytest.approx(
        1 - crown_frame["x"] - crown_frame["width"]
    )
    assert crown_frame["width"] > 0.8
