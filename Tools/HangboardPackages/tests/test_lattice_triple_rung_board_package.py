from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "lattice-triple-rung"
EXPECTED_HOLDS = (
    ("edge-45", "edge", 45),
    ("edge-10", "edge", 10),
    ("edge-20", "edge", 20),
)


def test_lattice_triple_rung_freezes_three_edges_as_model_package() -> None:
    board = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))

    assert board["id"] == "lattice-triple-rung"
    assert board["manufacturer"] == "Lattice Training"
    assert board["name"] == "Triple Rung"
    assert board["dimensions"] == "55 × 13 × 5 cm"
    assert [
        (
            presentation["id"],
            presentation["name"],
            presentation["media"]["assetPath"],
            presentation["isDefault"],
        )
        for presentation in board["presentations"]
    ] == [
        ("primary", "Primary", "assets/primary.usdz", True),
    ]
    assert tuple(
        (hold["id"], hold["kind"], hold.get("sizeMillimeters")) for hold in board["holds"]
    ) == EXPECTED_HOLDS
    for hold in board["holds"]:
        assert hold.get("depthRangeMillimeters") is None
        assert hold.get("gripType") is None
        assert hold.get("fingerCapacity") is None
        assert hold.get("features") is None

    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "holdGeometry" not in media
    assert {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file()
    } == {
        "board.json",
        "assets/primary.usdz",
        "assets/primary.model.json",
    }
    descriptor = json.loads(
        (PACKAGE_ROOT / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert descriptor["schemaVersion"] == 1
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (PACKAGE_ROOT / media["assetPath"]).read_bytes()
    ).hexdigest()
    assert set(descriptor["holds"]) == {hold["id"] for hold in board["holds"]}
    assert [node for node in descriptor["nodes"] if node["role"] == "body"] == [
        {"nodeID": "LatticeBody_editable_surface_001", "role": "body"},
    ]
    for hold_id, hold in descriptor["holds"].items():
        assert hold["nodeIDs"] == [
            node["nodeID"]
            for node in descriptor["nodes"]
            if node.get("holdID") == hold_id
        ]
