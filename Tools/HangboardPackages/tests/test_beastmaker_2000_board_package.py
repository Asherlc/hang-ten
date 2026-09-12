from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from hangboard_packages.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "beastmaker-2000"
EXPECTED_HOLDS = (
    *(f"top-sloper-{index}" for index in range(1, 5)),
    *(f"front-upper-{index}" for index in range(1, 3)),
    *(f"front-middle-{index}" for index in range(1, 10)),
    *(f"front-lower-{index}" for index in range(1, 10)),
    "hold-26",
    "hold-27",
    "hold-28",
)
EXPECTED_KINDS = {
    **{f"top-sloper-{index}": "sloper" for index in range(1, 5)},
    "front-upper-1": "pocket",
    "front-upper-2": "pocket",
    "front-middle-1": "edge",
    "front-middle-2": "pocket",
    "front-middle-3": "pocket",
    "front-middle-4": "pocket",
    "front-middle-5": "edge",
    "front-middle-6": "pocket",
    "front-middle-7": "pocket",
    "front-middle-8": "pocket",
    "front-middle-9": "edge",
    "front-lower-1": "edge",
    "front-lower-2": "pocket",
    "front-lower-3": "pocket",
    "front-lower-4": "pocket",
    "front-lower-5": "edge",
    "front-lower-6": "pocket",
    "front-lower-7": "pocket",
    "front-lower-8": "pocket",
    "front-lower-9": "edge",
    "hold-26": "pocket",
    "hold-27": "pocket",
    "hold-28": "sloper",
}
MIRRORED_PAIRS = (
    ("front-upper-1", "front-upper-2"),
    ("front-middle-1", "front-middle-9"),
    ("front-middle-2", "front-middle-8"),
    ("front-middle-3", "front-middle-7"),
    ("front-middle-4", "front-middle-6"),
    ("hold-26", "hold-27"),
    *((f"front-lower-{left}", f"front-lower-{10 - left}") for left in range(1, 5)),
)
EXPECTED_CENTERED_HOLDS = ("front-middle-5", "front-lower-5")


def test_beastmaker_2000_freezes_the_27_hold_inventory_as_model() -> None:
    board = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "beastmaker-2000"
    assert board["manufacturer"] == "Beastmaker"
    assert board["name"] == "Beastmaker 2000"
    assert board["dimensions"] == "580 × 150 × 58 mm"
    assert [
        (
            presentation["id"],
            presentation["name"],
            presentation["media"]["assetPath"],
            presentation["aspectRatio"],
            presentation["isDefault"],
        )
        for presentation in board["presentations"]
    ] == [
        ("primary", "Primary", "assets/primary.usdz", 3.8666664053333437, True),
    ]
    assert tuple(hold["id"] for hold in board["holds"]) == EXPECTED_HOLDS
    assert {hold["id"]: hold["kind"] for hold in board["holds"]} == EXPECTED_KINDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "sloper": 5,
        "edge": 6,
        "pocket": 16,
    }

    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "holdGeometry" not in media
    assert {path.relative_to(PACKAGE_ROOT).as_posix()
            for path in PACKAGE_ROOT.rglob("*") if path.is_file()} == {
        "board.json", "assets/primary.usdz", "assets/primary.model.json",
    }
    descriptor = json.loads(
        (PACKAGE_ROOT / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert descriptor["schemaVersion"] == 1
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (PACKAGE_ROOT / media["assetPath"]).read_bytes()
    ).hexdigest()
    assert set(descriptor["holds"]) == set(EXPECTED_HOLDS)
    assert [node for node in descriptor["nodes"] if node["role"] == "body"] == [
        {"nodeID": "BoardBody_surface_001", "role": "body"},
    ]
    for hold_id, hold in descriptor["holds"].items():
        assert hold["nodeIDs"] == [hold_id.replace("-", "_") + "_surface_001"]
        assert hold["nodeIDs"] == [
            node["nodeID"] for node in descriptor["nodes"]
            if node.get("holdID") == hold_id
        ]


def test_beastmaker_2000_model_pairs_preserve_mirrored_bounds_and_node_ownership() -> None:
    descriptor = json.loads(
        (PACKAGE_ROOT / "assets/primary.model.json").read_text(encoding="utf-8")
    )
    for left_id, right_id in MIRRORED_PAIRS:
        left = descriptor["holds"][left_id]
        right = descriptor["holds"][right_id]
        assert left["nodeIDs"] == [left_id.replace("-", "_") + "_surface_001"]
        assert right["nodeIDs"] == [right_id.replace("-", "_") + "_surface_001"]
        # Imported float32 coordinates retain symmetry within export precision.
        assert right["center"] == pytest.approx(
            [1 - left["center"][0], left["center"][1]], abs=1e-7
        )
        left_bounds, right_bounds = left["facePlaneAABB"], right["facePlaneAABB"]
        assert right_bounds["min"] == pytest.approx(
            [1 - left_bounds["max"][0], left_bounds["min"][1]], abs=1e-7
        )
        assert right_bounds["max"] == pytest.approx(
            [1 - left_bounds["min"][0], left_bounds["max"][1]], abs=1e-7
        )
    for hold_id in EXPECTED_CENTERED_HOLDS:
        assert descriptor["holds"][hold_id]["center"][0] == pytest.approx(0.5)


def test_beastmaker_2000_omits_unsupported_optional_metadata() -> None:
    holds = {
        hold.id: hold for hold in load_board_package(PACKAGE_ROOT).board.holds
    }

    assert all(hold.depth_range_millimeters is None for hold in holds.values())
    assert all(hold.hand_capacity is None for hold in holds.values())
    assert all(hold.grip_type is None for hold in holds.values())
    assert all(hold.features is None for hold in holds.values())
