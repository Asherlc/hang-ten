from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-project"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_package import load_board_package  # noqa: E402


SUPPORTED_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
EXPECTED_HOLDS = (
    ("jug-left", "jug", None, None),
    ("jug-right", "jug", None, None),
    ("sloper-flat-left", "sloper", 55, None),
    ("sloper-flat-right", "sloper", 55, None),
    ("pocket-45-three-left", "pocket", 45, 3),
    ("pocket-45-three-right", "pocket", 45, 3),
    ("edge-30-left", "edge", 30, None),
    ("edge-30-right", "edge", 30, None),
    ("pocket-40-two-left", "pocket", 40, 2),
    ("pocket-40-two-right", "pocket", 40, 2),
    ("pocket-22-three-left", "pocket", 22, 3),
    ("pocket-22-three-right", "pocket", 22, 3),
    ("pocket-22-two-left", "pocket", 22, 2),
    ("pocket-22-two-right", "pocket", 22, 2),
    ("sloper-round-center", "sloper", 53, None),
    ("edge-39-center", "edge", 39, None),
    ("edge-16-center", "edge", 16, None),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-flat-left", "sloper-flat-right"),
    ("pocket-45-three-left", "pocket-45-three-right"),
    ("edge-30-left", "edge-30-right"),
    ("pocket-40-two-left", "pocket-40-two-right"),
    ("pocket-22-three-left", "pocket-22-three-right"),
    ("pocket-22-two-left", "pocket-22-two-right"),
)
EXPECTED_PIXEL_FRAMES = {
    "jug-left": (
        (80.0, 225.0, 290.52, 67.25),
        (80.0, 280.382353, 58.542, 106.808824),
        (314.03, 280.382353, 56.49, 106.808824),
        (136.49, 341.698529, 177.54, 45.492647),
    ),
    "jug-right": (
        (1403.48, 225.0, 290.52, 67.25),
        (1635.458, 280.382353, 58.542, 106.808824),
        (1403.48, 280.382353, 56.49, 106.808824),
        (1459.97, 341.698529, 177.54, 45.492647),
    ),
    "sloper-flat-left": ((370.52, 260.602941, 274.38, 126.588235),),
    "sloper-flat-right": ((1129.10, 260.602941, 274.38, 126.588235),),
    "pocket-45-three-left": ((139.718, 290.845662, 177.54, 56.786691),),
    "pocket-45-three-right": ((1456.742, 290.845662, 177.54, 56.786691),),
    "edge-30-left": ((194.594, 392.096471, 242.10, 70.256470),),
    "edge-30-right": ((1337.306, 392.096471, 242.10, 70.256470),),
    "pocket-40-two-left": ((475.43, 392.294264, 96.84, 56.213088),),
    "pocket-40-two-right": ((1201.73, 392.294264, 96.84, 56.213088),),
    "pocket-22-three-left": ((254.312, 511.841029, 180.768, 65.232500),),
    "pocket-22-three-right": ((1338.92, 511.841029, 180.768, 65.232500),),
    "pocket-22-two-left": ((475.43, 507.093971, 96.84, 60.089853),),
    "pocket-22-two-right": ((1201.73, 507.093971, 96.84, 60.089853),),
    "sloper-round-center": ((644.90, 256.647059, 484.20, 130.544118),),
    "edge-39-center": ((604.55, 388.457059, 564.90, 77.851765),),
    "edge-16-center": ((604.55, 500.962353, 564.90, 72.155295),),
}


def _png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload[12:16] == b"IHDR"
    return struct.unpack(">II", payload[16:24])


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def test_metolius_project_preserves_audited_inventory_and_mirrored_contacts() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    presentation_size = _png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "metolius.project"
    assert board["manufacturer"] == "Metolius"
    assert board["name"] == "Project Training Board"
    assert board["dimensions"] == "622 × 152 mm"
    assert board["aspectRatio"] == 2.0
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    assert presentation_size == (1774, 887)
    assert math.isclose(
        presentation_size[0] / presentation_size[1],
        board["aspectRatio"],
        rel_tol=0.001,
    )
    assert tuple(
        (
            hold["id"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
        )
        for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert board_package._HOLD_KINDS == SUPPORTED_HOLD_KINDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "pocket": 8,
        "edge": 4,
        "sloper": 3,
        "jug": 2,
    }

    for hold in board["holds"]:
        for piece in hold["geometry"]:
            frame = piece["frame"]
            commands = piece["shape"]["commands"]
            assert piece["shape"]["type"] == "path"
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            assert any(command["command"] == "curve" for command in commands)
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            assert frame["width"] * frame["height"] > 0
            points = [point for command in commands for point in _points(command)]
            assert math.isclose(min(point[0] for point in points), 0.0, abs_tol=5e-7)
            assert math.isclose(min(point[1] for point in points), 0.0, abs_tol=5e-7)
            assert math.isclose(max(point[0] for point in points), 1.0, abs_tol=5e-7)
            assert math.isclose(max(point[1] for point in points), 1.0, abs_tol=5e-7)

        # Canonical Workbench coordinates are normalized to the complete
        # presentation image, including its intentional padding. A cropped
        # inner-board coordinate system would shift every path on package open.
        for piece, expected in zip(
            hold["geometry"],
            EXPECTED_PIXEL_FRAMES[hold["id"]],
            strict=True,
        ):
            frame = piece["frame"]
            actual = (
                frame["x"] * presentation_size[0],
                frame["y"] * presentation_size[1],
                frame["width"] * presentation_size[0],
                frame["height"] * presentation_size[1],
            )
            assert all(
                math.isclose(value, target, abs_tol=0.001)
                for value, target in zip(actual, expected, strict=True)
            )

    for left_id, right_id in MIRRORED_PAIRS:
        left_pieces = holds[left_id]["geometry"]
        right_pieces = holds[right_id]["geometry"]
        assert len(left_pieces) == len(right_pieces)
        for left, right in zip(left_pieces, right_pieces, strict=True):
            left_frame = left["frame"]
            right_frame = right["frame"]
            assert math.isclose(
                right_frame["x"],
                1 - left_frame["x"] - left_frame["width"],
                abs_tol=5e-10,
            )
            assert math.isclose(right_frame["y"], left_frame["y"], abs_tol=5e-10)
            assert math.isclose(
                right_frame["width"], left_frame["width"], abs_tol=5e-10
            )
            assert math.isclose(
                right_frame["height"], left_frame["height"], abs_tol=5e-10
            )
            assert right.get("treatment") == left.get("treatment")
            for left_command, right_command in zip(
                left["shape"]["commands"], right["shape"]["commands"], strict=True
            ):
                assert left_command["command"] == right_command["command"]
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=5e-10)
                    assert math.isclose(right_y, left_y, abs_tol=5e-10)

    assert len(holds["jug-left"]["geometry"]) == 4
    assert len(holds["jug-right"]["geometry"]) == 4
    assert all(len(holds[hold_id]["geometry"]) == 1 for hold_id in (
        "sloper-flat-left", "sloper-flat-right", "sloper-round-center",
        "pocket-45-three-left", "pocket-45-three-right",
        "edge-30-left", "edge-30-right",
        "pocket-40-two-left", "pocket-40-two-right",
        "pocket-22-three-left", "pocket-22-three-right",
        "pocket-22-two-left", "pocket-22-two-right",
        "edge-39-center", "edge-16-center",
    ))

    top_ids = (
        "jug-left", "sloper-flat-left", "sloper-round-center",
        "sloper-flat-right", "jug-right",
    )
    for left_id, right_id in zip(top_ids, top_ids[1:]):
        left_frame = package.hold_frame(left_id)
        right_frame = package.hold_frame(right_id)
        assert math.isclose(
            left_frame.x + left_frame.width,
            right_frame.x,
            abs_tol=1e-12,
        )

    assert holds["jug-left"]["features"] == ["jug"]
    assert holds["jug-right"]["features"] == ["jug"]
    assert holds["sloper-round-center"]["features"] == ["roundSloper"]
    assert all(holds[hold_id]["gripType"] == "sloper" for hold_id in (
        "sloper-flat-left", "sloper-flat-right", "sloper-round-center",
    ))
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    forbidden_keys = {"cueStyle", "semantics", "evidence", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(raw_document))
