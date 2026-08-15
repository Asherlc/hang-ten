from __future__ import annotations

from pathlib import Path
import struct
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package


PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "lattice-triple-rung"
EXPECTED_HOLDS = (
    ("edge-45", "edge", 45, (0.046875, 0.328125, 0.90625, 0.04357434)),
    ("edge-10", "edge", 10, (0.035156, 0.467773, 0.929688, 0.05304736)),
    ("edge-20", "edge", 20, (0.029297, 0.594727, 0.941406, 0.0634671)),
)


def test_lattice_triple_rung_has_three_exact_continuous_edge_regions() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board

    assert board["id"] == "lattice-triple-rung"
    assert board["manufacturer"] == "Lattice Training"
    assert board["name"] == "Triple Rung"
    assert board["dimensions"] == "55 × 13 × 5 cm"
    assert board["aspectRatio"] == 1.5
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert tuple(
        (hold["id"], hold["kind"], hold["sizeMillimeters"])
        for hold in board["holds"]
    ) == tuple(expected[:3] for expected in EXPECTED_HOLDS)

    for hold, expected in zip(board["holds"], EXPECTED_HOLDS, strict=True):
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        assert tuple(piece["frame"].values()) == pytest.approx(expected[3], abs=1e-9)
        assert piece["shape"]["type"] == "path"
        assert piece["shape"]["commands"][0]["command"] == "move"
        assert piece["shape"]["commands"][-1]["command"] == "close"
        assert len(piece["shape"]["commands"]) >= 8
        assert piece["frame"]["width"] * piece["frame"]["height"] > 0
        assert piece["frame"]["x"] >= 0
        assert piece["frame"]["y"] >= 0
        assert piece["frame"]["x"] + piece["frame"]["width"] <= 1
        assert piece["frame"]["y"] + piece["frame"]["height"] <= 1
        assert "depthRangeMillimeters" not in hold
        assert "gripType" not in hold
        assert "fingerCapacity" not in hold
        assert "features" not in hold


def test_lattice_triple_rung_aspect_ratio_matches_its_primary_png_ihdr() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    image = (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()

    assert image[:8] == b"\x89PNG\r\n\x1a\n"
    length, chunk_type = struct.unpack(">I4s", image[8:16])
    assert chunk_type == b"IHDR"
    assert length == 13
    width, height = struct.unpack(">II", image[16:24])
    assert (width, height) == (1536, 1024)
    assert board["aspectRatio"] == width / height == 1.5
