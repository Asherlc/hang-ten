from __future__ import annotations

from pathlib import Path
import struct
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package
from board_geometry import display_path_for_shape


PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "lattice-triple-rung"
EXPECTED_HOLDS = (
    ("edge-45", "edge", 45, (0.046875, 0.328125, 0.90625, 0.04357434)),
    ("edge-10", "edge", 10, (0.035156, 0.467773, 0.929688, 0.05304736)),
    ("edge-20", "edge", 20, (0.029297, 0.594727, 0.941406, 0.0634671)),
)
EXPECTED_PATH_COMMANDS = (
    [
        {"command": "move", "to": [0.01799999999999999, 0.0]},
        {"command": "curve", "control1": [0.006000000000000005, 0.07216494845360766], "control2": [0.0, 0.24742268041237128], "to": [0.0, 0.47422680412371165]},
        {"command": "curve", "control1": [0.0, 0.7113402061855668], "control2": [0.003999999999999996, 0.9278350515463923], "to": [0.011999999999999995, 1.0]},
        {"command": "curve", "control1": [0.30000000000000004, 0.9587628865979381], "control2": [0.7000000000000001, 0.9587628865979381], "to": [0.988, 1.0]},
        {"command": "curve", "control1": [0.996, 0.9278350515463923], "control2": [1.0, 0.7113402061855668], "to": [1.0, 0.47422680412371165]},
        {"command": "curve", "control1": [1.0, 0.24742268041237128], "control2": [0.9939999999999999, 0.07216494845360766], "to": [0.982, 0.0]},
        {"command": "curve", "control1": [0.72, 0.03608247422680383], "control2": [0.27999999999999997, 0.03608247422680383], "to": [0.01799999999999999, 0.0]},
        {"command": "close"},
    ],
    [
        {"command": "move", "to": [0.011999999999999997, 0.0309278350515469]},
        {"command": "curve", "control1": [0.003000000000000001, 0.1237113402061855], "control2": [0.0, 0.30927835051546376], "to": [0.0, 0.5360824742268039]},
        {"command": "curve", "control1": [0.0, 0.7731958762886609], "control2": [0.003999999999999999, 0.9381443298969083], "to": [0.011000000000000006, 1.0]},
        {"command": "curve", "control1": [0.30999999999999994, 0.9690721649484542], "control2": [0.6900000000000001, 0.9690721649484542], "to": [0.9889999999985996, 1.0]},
        {"command": "curve", "control1": [0.9960000000014007, 0.9381443298969083], "control2": [1.0, 0.7731958762886609], "to": [1.0, 0.5360824742268039]},
        {"command": "curve", "control1": [1.0, 0.30927835051546376], "control2": [0.9970000000028012, 0.1237113402061855], "to": [0.9879999999971989, 0.0309278350515469]},
        {"command": "curve", "control1": [0.72, 0.0], "control2": [0.27999999999999997, 0.0], "to": [0.011999999999999997, 0.0309278350515469]},
        {"command": "close"},
    ],
    [
        {"command": "move", "to": [0.009999999999999997, 0.04123711340206164]},
        {"command": "curve", "control1": [0.002000000000000001, 0.14432989690721573], "control2": [0.0, 0.32989690721649484], "to": [0.0, 0.5463917525773202]},
        {"command": "curve", "control1": [0.0, 0.7731958762886593], "control2": [0.003999999999999998, 0.9381443298969075], "to": [0.009999999999999997, 1.0]},
        {"command": "curve", "control1": [0.31, 0.9690721649484537], "control2": [0.69, 0.9690721649484537], "to": [0.99, 1.0]},
        {"command": "curve", "control1": [0.9960000000027662, 0.9381443298969075], "control2": [1.0, 0.7731958762886593], "to": [1.0, 0.5463917525773202]},
        {"command": "curve", "control1": [1.0, 0.32989690721649484], "control2": [0.998000000001383, 0.14432989690721573], "to": [0.99, 0.04123711340206164]},
        {"command": "curve", "control1": [0.7199999999999999, 0.0], "control2": [0.27999999999999997, 0.0], "to": [0.009999999999999997, 0.04123711340206164]},
        {"command": "close"},
    ],
)
EXPECTED_DISPLAY_PATHS = (
    "M 97.056 336 C 80.352 339.22000896 72 347.04003072 72 357.16005888 C 72 367.74008832 77.568 377.4001152 88.704 380.62012416 C 489.6 378.78011904 1046.4 378.78011904 1447.296 380.62012416 C 1458.432 377.4001152 1464 367.74008832 1464 357.16005888 C 1464 347.04003072 1455.648 339.22000896 1438.944 336 C 1074.24 337.61000448 461.76 337.61000448 97.056 336 Z",
    "M 71.135625216 480.67956736 C 58.283618304 485.71961344 53.999616 495.7997056 53.999616 508.11981824 C 53.999616 520.999936 59.711619072 529.96001792 69.707624448 533.32004864 C 496.67985408 531.64003328 1039.32014592 531.64003328 1466.29237555 533.32004864 C 1476.28838093 529.96001792 1482.000384 520.999936 1482.000384 508.11981824 C 1482.000384 495.7997056 1477.7163817 485.71961344 1464.86437478 480.67956736 C 1082.16016896 478.999552 453.83983104 478.999552 71.135625216 480.67956736 Z",
    "M 59.46018816 611.6804608 C 47.892191232 618.3804928 45.000192 630.4405504 45.000192 644.5106176 C 45.000192 659.250688 50.784190464 669.9707392 59.46018816 673.9907584 C 493.26007296 671.9807488 1042.73992704 671.9807488 1476.53981184 673.9907584 C 1485.21580954 669.9707392 1490.999808 659.250688 1490.999808 644.5106176 C 1490.999808 630.4405504 1488.10780877 618.3804928 1476.53981184 611.6804608 C 1086.11991552 609.000448 449.88008448 609.000448 59.46018816 611.6804608 Z",
)


def test_lattice_triple_rung_has_three_exact_continuous_edge_regions() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board

    assert board["id"] == "lattice-triple-rung"
    assert board["manufacturer"] == "Lattice Training"
    assert board["name"] == "Triple Rung"
    assert board["subtitle"] == "Three continuous rounded wooden edges."
    assert board["productURL"] == "https://latticetraining.com/product/triple-rung-wooden-hangboard/"
    assert board["dimensions"] == "55 × 13 × 5 cm"
    assert board["aspectRatio"] == 1.5
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert tuple(
        (hold["id"], hold["kind"], hold["sizeMillimeters"])
        for hold in board["holds"]
    ) == tuple(expected[:3] for expected in EXPECTED_HOLDS)

    for hold, expected, expected_commands, expected_path in zip(
        board["holds"],
        EXPECTED_HOLDS,
        EXPECTED_PATH_COMMANDS,
        EXPECTED_DISPLAY_PATHS,
        strict=True,
    ):
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        assert tuple(piece["frame"].values()) == pytest.approx(expected[3], abs=1e-9)
        assert piece["shape"]["type"] == "path"
        assert piece["shape"]["commands"] == expected_commands
        assert display_path_for_shape(
            piece["frame"], piece["shape"], 1536, 1024, label=hold["id"]
        ).data == expected_path
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
