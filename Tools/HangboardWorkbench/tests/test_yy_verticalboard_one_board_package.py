from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
if str(WORKBENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "yy-verticalboard-one"
PRIMARY_SHA256 = "f0236f9b7f2f8f651627345359d4b8637a21017e9ee208720284ada61bcc3a9a"
SUPPORTED_KINDS = ("jug", "edge", "pocket", "pinch", "sloper")
EXPECTED_HOLDS = (
    ("jug-left", "jug"),
    ("jug-right", "jug"),
    ("sloper-35-left", "sloper"),
    ("sloper-20-center", "sloper"),
    ("sloper-35-right", "sloper"),
    ("edge-25-top-left", "edge"),
    ("pocket-30-left", "pocket"),
    ("pocket-30-right", "pocket"),
    ("edge-25-top-right", "edge"),
    ("edge-45-left", "edge"),
    ("pocket-50-left", "pocket"),
    ("edge-25-inclined-left", "edge"),
    ("edge-25-inclined-right", "edge"),
    ("pocket-50-right", "pocket"),
    ("edge-45-right", "edge"),
    ("handle-center", "jug"),
    ("edge-20-left", "edge"),
    ("edge-18-left", "edge"),
    ("edge-18-right", "edge"),
    ("edge-20-right", "edge"),
)
EXPECTED_PIECE_COUNTS = (
    ("jug-left", 1),
    ("jug-right", 1),
    ("sloper-35-left", 1),
    ("sloper-20-center", 5),
    ("sloper-35-right", 1),
    ("edge-25-top-left", 1),
    ("pocket-30-left", 1),
    ("pocket-30-right", 1),
    ("edge-25-top-right", 1),
    ("edge-45-left", 1),
    ("pocket-50-left", 1),
    ("edge-25-inclined-left", 1),
    ("edge-25-inclined-right", 1),
    ("pocket-50-right", 1),
    ("edge-45-right", 1),
    ("handle-center", 1),
    ("edge-20-left", 1),
    ("edge-18-left", 1),
    ("edge-18-right", 1),
    ("edge-20-right", 1),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-35-left", "sloper-35-right"),
    ("edge-25-top-left", "edge-25-top-right"),
    ("pocket-30-left", "pocket-30-right"),
    ("edge-45-left", "edge-45-right"),
    ("pocket-50-left", "pocket-50-right"),
    ("edge-25-inclined-left", "edge-25-inclined-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-18-left", "edge-18-right"),
)


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value))
    return set()


def _png_ihdr_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return struct.unpack(">II", header[16:24])


def test_yy_verticalboard_one_preserves_audited_physical_package() -> None:
    # Break caught: a missing or malformed canonical package cannot silently stage.
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    # Break caught: product identity or presentation canvas drifts from P1/P5.
    assert board["id"] == "yy.verticalboard-one"
    assert board["manufacturer"] == "YY Vertical"
    assert board["name"] == "VerticalBoard One"
    assert board["subtitle"] == "Poplar climbing training hangboard."
    assert board["productURL"] == (
        "https://www.yyvertical.com/en/collections/training/products/verticalboard-one"
    )
    assert board["dimensions"] == "62 × 13 × 5.5 cm"
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert _png_ihdr_dimensions(PACKAGE_ROOT / "assets" / "primary.png") == (1774, 887)
    assert board["aspectRatio"] == 1774 / 887

    # Break caught: a physical contact is dropped, duplicated, reordered, or reclassified.
    assert tuple((hold["id"], hold["kind"]) for hold in board["holds"]) == EXPECTED_HOLDS
    assert all(hold["kind"] in SUPPORTED_KINDS for hold in board["holds"])
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "jug": 3,
        "edge": 10,
        "pocket": 4,
        "sloper": 3,
    }

    # Break caught: the center 20-degree plane is flattened across its two pocket openings.
    assert tuple((hold["id"], len(hold["geometry"])) for hold in board["holds"]) == (
        EXPECTED_PIECE_COUNTS
    )
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 24
    center_pieces = holds["sloper-20-center"]["geometry"]
    assert center_pieces[0]["frame"]["x"] == pytest.approx(
        1 - center_pieces[0]["frame"]["x"] - center_pieces[0]["frame"]["width"],
        abs=1e-12,
    )
    assert center_pieces[1]["frame"]["x"] == pytest.approx(
        1 - center_pieces[1]["frame"]["x"] - center_pieces[1]["frame"]["width"],
        abs=1e-12,
    )
    assert center_pieces[4]["frame"]["x"] == pytest.approx(
        1 - center_pieces[4]["frame"]["x"] - center_pieces[4]["frame"]["width"],
        abs=1e-12,
    )
    assert center_pieces[3]["frame"]["x"] == pytest.approx(
        1 - center_pieces[2]["frame"]["x"] - center_pieces[2]["frame"]["width"],
        abs=1e-12,
    )
    assert center_pieces[3]["frame"]["y"] == center_pieces[2]["frame"]["y"]
    assert center_pieces[3]["frame"]["width"] == center_pieces[2]["frame"]["width"]
    assert center_pieces[3]["frame"]["height"] == center_pieces[2]["frame"]["height"]

    # Break caught: highlight/hit paths become open, boxy, empty, or leave normalized space.
    for hold in board["holds"]:
        for piece in hold["geometry"]:
            shape = piece["shape"]
            commands = shape["commands"]
            assert shape["type"] == "path"
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            assert sum(command["command"] in {"curve", "quad"} for command in commands) >= 2
            frame = piece["frame"]
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            points = [point for command in commands for point in _points(command)]
            assert all(math.isfinite(value) for point in points for value in point)
            assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
            assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
            assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
            assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)

    # Break caught: a source-symmetric left/right contact drifts independently.
    for left_id, right_id in MIRRORED_PAIRS:
        left_pieces = holds[left_id]["geometry"]
        right_pieces = holds[right_id]["geometry"]
        assert len(left_pieces) == len(right_pieces)
        for left, right in zip(left_pieces, right_pieces, strict=True):
            left_frame = left["frame"]
            right_frame = right["frame"]
            assert right_frame["x"] == pytest.approx(
                1 - left_frame["x"] - left_frame["width"], abs=1e-12
            )
            assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-12)
            assert right_frame["width"] == pytest.approx(left_frame["width"], abs=1e-12)
            assert right_frame["height"] == pytest.approx(left_frame["height"], abs=1e-12)
            assert right["treatment"] == left["treatment"]
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

    # Break caught: unsupported optional semantics enter the minimum physical package.
    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    assert all(
        set(raw_hold) == {"id", "name", "kind", "geometry"}
        for raw_hold in raw_document["holds"]
    )
    assert {
        "cueStyle",
        "claims",
        "semantics",
        "evidence",
        "artwork",
        "catalog",
        "ui",
        "instructions",
        "shortLabel",
        "sizeMillimeters",
        "depthRangeMillimeters",
        "gripType",
        "fingerCapacity",
        "features",
    }.isdisjoint(_all_keys(raw_document))

    # Break caught: package sidecars appear or the approved raster is replaced/re-encoded.
    assert {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*")
    } == {"assets", "assets/primary.png", "board.json"}
    assert hashlib.sha256(
        (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()
    ).hexdigest() == PRIMARY_SHA256
