from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hangboard_packages.cad_source import load_board, package_source_path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "trango-rock-prodigy-training-center"


def test_training_center_is_a_hash_bound_model_only_package() -> None:
    source = package_source_path(PACKAGE_ROOT)
    board = load_board(source)
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
    } == {"assets/primary.usdz", "assets/primary.model.json"}

    descriptor = json.loads(
        (PACKAGE_ROOT / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert descriptor["schemaVersion"] == 2
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (PACKAGE_ROOT / media["assetPath"]).read_bytes()
    ).hexdigest()
    contact_ids = {contact["id"] for contact in board["contacts"]}
    assert len(contact_ids) == 24
    assert set(descriptor["contactSlots"]) == {cid.rsplit("-", 1)[0] for cid in contact_ids}
    assert [node["nodeID"] for node in descriptor["nodes"] if node["role"] == "body"] == [
        "body_001",
    ]
    for contact_id, contact in descriptor["contactSlots"].items():
        assert contact["nodeIDs"] == [
            node["nodeID"]
            for node in descriptor["nodes"]
            if node.get("contactSlotID") == contact_id
        ]

    assert {
        node["nodeID"]: node["contactSlotID"]
        for node in descriptor["nodes"]
        if node["nodeID"].startswith("pinch_")
    } == {
        "pinch_medium_left_001": "pinch-medium",
        "pinch_wide_left_001": "pinch-wide",
    }
    assert descriptor["contactSlots"]["pinch-medium"]["facePlaneAABB"] != (
        descriptor["contactSlots"]["pinch-wide"]["facePlaneAABB"]
    )
