from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _aabbs_overlap(
    first: dict[str, list[float]], second: dict[str, list[float]]
) -> bool:
    return not (
        first["max"][0] <= second["min"][0]
        or second["max"][0] <= first["min"][0]
        or first["max"][1] <= second["min"][1]
        or second["max"][1] <= first["min"][1]
    )


def test_moon_armstrong_model_descriptor_is_complete_with_reviewed_right_side_separations() -> None:
    root = REPO_ROOT / "Hangboards" / "moon-armstrong"
    board = json.loads((root / "board.json").read_text(encoding="utf-8"))
    media = board["presentations"][0]["media"]

    assert len(board["presentations"]) == 1
    assert media["type"] == "model"
    assert media["assetPath"] == "assets/primary.usdz"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "contactGeometry" not in media
    assert {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    } == {"board.json", "assets/primary.usdz", "assets/primary.model.json"}

    descriptor = json.loads(
        (root / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert descriptor["schemaVersion"] == 1
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (root / media["assetPath"]).read_bytes()
    ).hexdigest()

    assert len(board["contacts"]) == 21
    contact_ids = {contact["id"] for contact in board["contacts"]}
    contact_nodes = [
        node for node in descriptor["nodes"] if node["role"] == "contact"
    ]
    assert len(contact_ids) == 21
    assert set(descriptor["contacts"]) == contact_ids
    assert {node["contactID"] for node in contact_nodes} == contact_ids
    assert len(contact_nodes) == len(contact_ids)
    assert len({node["nodeID"] for node in contact_nodes}) == len(contact_nodes)
    for contact_id in contact_ids:
        assert descriptor["contacts"][contact_id]["nodeIDs"] == [
            node["nodeID"]
            for node in contact_nodes
            if node["contactID"] == contact_id
        ]
        assert len(descriptor["contacts"][contact_id]["nodeIDs"]) == 1
        bounds = descriptor["contacts"][contact_id]["facePlaneAABB"]
        assert len(bounds["min"]) == 2
        assert len(bounds["max"]) == 2
        assert all(0 <= value <= 1 for value in bounds["min"] + bounds["max"])
        assert all(low <= high for low, high in zip(bounds["min"], bounds["max"]))

    # Retained descriptor bounds preserve the reviewed right-side separations.
    edge_8 = descriptor["contacts"]["edge-8-right"]["facePlaneAABB"]
    mono = descriptor["contacts"]["mono-right"]["facePlaneAABB"]
    two_finger = descriptor["contacts"]["two-finger-pocket-right"]["facePlaneAABB"]
    assert not _aabbs_overlap(edge_8, mono)
    assert not _aabbs_overlap(edge_8, two_finger)
    assert not _aabbs_overlap(mono, two_finger)
