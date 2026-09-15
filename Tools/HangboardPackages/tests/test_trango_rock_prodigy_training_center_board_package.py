from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "trango-rock-prodigy-training-center"


def test_training_center_is_a_hash_bound_model_only_package() -> None:
    board = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    presentations = board["presentations"]
    assert isinstance(presentations, list) and len(presentations) == 1
    media = presentations[0]["media"]
    assert media["type"] == "model"
    assert media["assetPath"] == "assets/primary.usdz"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "contactGeometry" not in media
    assert {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file()
    } == {"board.json", "assets/primary.usdz", "assets/primary.model.json"}

    descriptor = json.loads(
        (PACKAGE_ROOT / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert descriptor["schemaVersion"] == 1
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (PACKAGE_ROOT / media["assetPath"]).read_bytes()
    ).hexdigest()
    contact_ids = {contact["id"] for contact in board["contacts"]}
    assert len(contact_ids) == 24
    assert set(descriptor["contacts"]) == contact_ids
    assert [node["nodeID"] for node in descriptor["nodes"] if node["role"] == "body"] == [
        "body_left_001", "body_right_001",
    ]
    for contact_id, contact in descriptor["contacts"].items():
        assert contact["nodeIDs"] == [
            node["nodeID"]
            for node in descriptor["nodes"]
            if node.get("contactID") == contact_id
        ]

    assert {
        node["nodeID"]: node["contactID"]
        for node in descriptor["nodes"]
        if node["nodeID"].startswith("pinch_combination_")
    } == {
        "pinch_combination_left_001": "pinch-medium-left",
        "pinch_combination_left_002": "pinch-wide-left",
        "pinch_combination_right_001": "pinch-medium-right",
        "pinch_combination_right_002": "pinch-wide-right",
    }
