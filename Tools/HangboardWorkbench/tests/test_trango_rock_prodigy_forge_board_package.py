from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "trango-rock-prodigy-forge"
EXPECTED_HOLDS = (
    ("pinch-variable-left", "pinch", 2),
    ("pinch-variable-right", "pinch", 2),
    ("sloper-30-left", "sloper", 1),
    ("sloper-30-right", "sloper", 1),
    ("sloper-40-left", "sloper", 1),
    ("sloper-40-right", "sloper", 1),
    ("edge-large-flat-left", "edge", 1),
    ("edge-large-flat-right", "edge", 1),
    ("edge-slopey-crimper-left", "edge", 1),
    ("edge-slopey-crimper-right", "edge", 1),
    ("edge-variable-7-20-left", "edge", 1),
    ("edge-variable-7-20-right", "edge", 1),
    ("pocket-mr-deep-25-left", "pocket", 1),
    ("pocket-mr-deep-25-right", "pocket", 1),
    ("pocket-mr-shallow-15-left", "pocket", 1),
    ("pocket-mr-shallow-15-right", "pocket", 1),
    ("edge-closed-crimp-left", "edge", 2),
    ("edge-closed-crimp-right", "edge", 2),
    ("pocket-imr-variable-19-31-left", "pocket", 1),
    ("pocket-imr-variable-19-31-right", "pocket", 1),
)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index][0], EXPECTED_HOLDS[index + 1][0])
    for index in range(0, len(EXPECTED_HOLDS), 2)
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    assert isinstance(command, dict)
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_recursive_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_recursive_keys(child) for child in value))
    return set()


def test_trango_rock_prodigy_forge_preserves_audited_physical_package() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board["id"] == "trango.rock-prodigy-forge"
    assert board["manufacturer"] == "Trango"
    assert board["name"] == "Rock Prodigy Forge"
    assert board["dimensions"] == "Each piece: 12.75 × 5.25 in"
    primary_header = (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()[:24]
    assert primary_header[:8] == b"\x89PNG\r\n\x1a\n"
    assert primary_header[8:16] == b"\x00\x00\x00\rIHDR"
    width, height = struct.unpack(">II", primary_header[16:24])
    assert (width, height) == (1536, 1024)
    assert board["aspectRatio"] == width / height
    assert board["presentation"]["assetPath"] == "assets/primary.png"

    assert tuple(
        (hold["id"], hold["kind"], len(hold["geometry"])) for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert frozenset(board_package._HOLD_KINDS) == {
        "jug",
        "edge",
        "pocket",
        "pinch",
        "sloper",
    }

    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "edge": 8,
        "pocket": 6,
        "sloper": 4,
        "pinch": 2,
    }
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 24

    for hold in board["holds"]:
        for piece in hold["geometry"]:
            assert piece["shape"]["type"] == "path"
            assert piece["shape"]["commands"][0]["command"] == "move"
            assert piece["shape"]["commands"][-1]["command"] == "close"
            assert sum(
                command["command"] == "curve" for command in piece["shape"]["commands"]
            ) >= 4
            assert 0 <= piece["frame"]["x"] < piece["frame"]["x"] + piece["frame"]["width"] <= 1
            assert 0 <= piece["frame"]["y"] < piece["frame"]["y"] + piece["frame"]["height"] <= 1
            assert piece["frame"]["width"] * piece["frame"]["height"] > 0
            local_points = [
                point
                for command in piece["shape"]["commands"]
                for point in _points(command)
            ]
            assert min(x for x, _ in local_points) == pytest.approx(0, abs=5e-7)
            assert min(y for _, y in local_points) == pytest.approx(0, abs=5e-7)
            assert max(x for x, _ in local_points) == pytest.approx(1, abs=5e-7)
            assert max(y for _, y in local_points) == pytest.approx(1, abs=5e-7)

    for left_id, right_id in MIRRORED_PAIRS:
        left_pieces = holds[left_id]["geometry"]
        right_pieces = holds[right_id]["geometry"]
        assert len(left_pieces) == len(right_pieces)
        for left, right in zip(left_pieces, right_pieces, strict=True):
            assert right["frame"]["x"] == pytest.approx(
                1 - left["frame"]["x"] - left["frame"]["width"], abs=1e-12
            )
            assert right["frame"]["y"] == pytest.approx(left["frame"]["y"], abs=1e-12)
            assert right["frame"]["width"] == pytest.approx(left["frame"]["width"], abs=1e-12)
            assert right["frame"]["height"] == pytest.approx(left["frame"]["height"], abs=1e-12)
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

    for hold_id in ("pinch-variable-left", "pinch-variable-right"):
        assert holds[hold_id]["features"] == [
            "widePinch",
            "mediumPinch",
            "smallPinch",
        ]
    for hold_id in (
        "sloper-30-left",
        "sloper-30-right",
        "sloper-40-left",
        "sloper-40-right",
    ):
        assert holds[hold_id]["gripType"] == "sloper"
    for hold_id in ("edge-variable-7-20-left", "edge-variable-7-20-right"):
        depth_range = holds[hold_id]["depthRangeMillimeters"]
        assert (depth_range["lowerBound"], depth_range["upperBound"]) == (7, 20)
    for hold_id in ("pocket-mr-deep-25-left", "pocket-mr-deep-25-right"):
        hold = holds[hold_id]
        assert (hold["sizeMillimeters"], hold["fingerCapacity"], hold["gripType"]) == (
            25,
            2,
            "twoFingerPocket",
        )
        assert hold["features"] == [
            "pocket",
            "twoFingerPocket",
            "deepTwoFingerPocket",
        ]
    for hold_id in ("pocket-mr-shallow-15-left", "pocket-mr-shallow-15-right"):
        hold = holds[hold_id]
        assert (
            hold["sizeMillimeters"],
            hold["fingerCapacity"],
            hold["gripType"],
        ) == (
            15,
            2,
            "twoFingerPocket",
        )
        assert hold["features"] == ["pocket", "twoFingerPocket"]
    for hold_id in ("edge-closed-crimp-left", "edge-closed-crimp-right"):
        hold = holds[hold_id]
        assert hold.get("sizeMillimeters") is None
        assert hold["gripType"] == "fullCrimp"
        assert hold["features"] == ["thinCrimp"]
        assert tuple(piece["treatment"]["type"] for piece in hold["geometry"]) == (
            "recess",
            "surface",
        )
    for hold_id in (
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    ):
        hold = holds[hold_id]
        depth_range = hold["depthRangeMillimeters"]
        assert (depth_range["lowerBound"], depth_range["upperBound"]) == (19, 31)
        assert (hold["fingerCapacity"], hold["gripType"]) == (3, "threeFingerPocket")
        assert hold["features"] == ["pocket", "threeFingerPocket"]

    sized_ids = {
        "pocket-mr-deep-25-left",
        "pocket-mr-deep-25-right",
        "pocket-mr-shallow-15-left",
        "pocket-mr-shallow-15-right",
    }
    ranged_ids = {
        "edge-variable-7-20-left",
        "edge-variable-7-20-right",
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    }
    grip_ids = {
        "sloper-30-left",
        "sloper-30-right",
        "sloper-40-left",
        "sloper-40-right",
        *sized_ids,
        "edge-closed-crimp-left",
        "edge-closed-crimp-right",
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    }
    capacity_ids = sized_ids | {
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    }
    feature_ids = capacity_ids | {
        "pinch-variable-left",
        "pinch-variable-right",
        "edge-closed-crimp-left",
        "edge-closed-crimp-right",
    }
    assert all(
        hold.get("sizeMillimeters") is None
        for hold in board["holds"]
        if hold["id"] not in sized_ids
    )
    assert all(
        hold.get("depthRangeMillimeters") is None
        for hold in board["holds"]
        if hold["id"] not in ranged_ids
    )
    assert all(
        hold.get("gripType") is None for hold in board["holds"] if hold["id"] not in grip_ids
    )
    assert all(
        hold.get("fingerCapacity") is None
        for hold in board["holds"]
        if hold["id"] not in capacity_ids
    )
    assert all(
        hold.get("features") is None for hold in board["holds"] if hold["id"] not in feature_ids
    )

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {
        "cueStyle",
        "claims",
        "semantics",
        "evidence",
        "artwork",
        "catalog",
        "ui",
        "instructions",
    }
    assert forbidden.isdisjoint(_recursive_keys(raw))


def test_forge_40_degree_slopers_stay_above_lower_board_silhouette() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    for hold_id in ("sloper-40-left", "sloper-40-right"):
        piece = holds[hold_id]["geometry"][0]
        for command in piece["shape"]["commands"]:
            for local_x, local_y in _points(command):
                global_x = piece["frame"]["x"] + local_x * piece["frame"]["width"]
                global_y = piece["frame"]["y"] + local_y * piece["frame"]["height"]
                left_x = global_x if hold_id.endswith("-left") else 1 - global_x
                if 0.079 <= left_x <= 0.201:
                    # Hand-audited against the diagonal lower silhouette in
                    # assets/primary.png: from about (0.08, 0.658) at the
                    # outside corner to (0.20, 0.610) at the inside corner.
                    assert global_y <= 0.69 - 0.4 * left_x + 1e-12
