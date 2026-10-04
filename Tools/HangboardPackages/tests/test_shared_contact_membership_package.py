"""Package parser validates the same physical-surface membership contract."""
import hashlib
import json

import pytest
from hangboard_packages.board_catalog import _load_model_descriptor


def payload():
    return {"schemaVersion": 1, "coordinateFrame": "hang-ten-board-v1",
            "modelSHA256": hashlib.sha256(b"mesh").hexdigest(),
            "modelBounds": {"min": [-.065, -.03, -.02], "max": [.065, .03, .02]},
            "nodes": [{"nodeID": "body", "role": "body"},
                      {"nodeID": "bottom", "role": "contact", "contactID": "pinch"},
                      {"nodeID": "top", "role": "contact", "contactID": "jug", "additionalContactIDs": ["pinch"]}],
            "contacts": {"jug": {"nodeIDs": ["top"], "facePlaneAABB": {"min": [.1, .95], "max": [.9, 1]}, "center": [.5, .975]},
                         "pinch": {"nodeIDs": ["bottom", "top"], "facePlaneAABB": {"min": [.1, 0], "max": [.9, 1]}, "center": [.5, .5]}}}


def load(tmp_path, data):
    descriptor = tmp_path / "model.json"
    descriptor.write_text(json.dumps(data))
    asset = tmp_path / "model.usdz"
    asset.write_bytes(b"mesh")
    return _load_model_descriptor(descriptor, asset, {"jug", "pinch"})


def test_shared_pinch_loads_both_nodes_without_changing_jug(tmp_path):
    assert set(load(tmp_path, payload())) == {"jug", "pinch"}


@pytest.mark.parametrize("extras", [[], None, "pinch", [""], [1], ["jug"], ["pinch", "pinch"], ["z", "a"], ["unknown"]])
def test_malformed_shared_membership_fails_closed(tmp_path, extras):
    data = payload()
    data["nodes"][-1]["additionalContactIDs"] = extras
    with pytest.raises(ValueError):
        load(tmp_path, data)


@pytest.mark.parametrize("role", ["body", "attachment"])
def test_other_roles_cannot_declare_shared_contact_membership(tmp_path, role):
    data = payload()
    data["nodes"][0].update(role=role, additionalContactIDs=["pinch"])
    with pytest.raises(ValueError):
        load(tmp_path, data)


def test_shared_membership_requires_both_declared_nodes(tmp_path):
    data = payload()
    data["contacts"]["pinch"]["nodeIDs"] = ["bottom"]
    with pytest.raises(ValueError, match="exactly match"):
        load(tmp_path, data)


def test_shared_membership_cannot_be_replaced_by_an_outline(tmp_path):
    data = payload()
    data["contacts"]["pinch"]["outline"] = [[.1, 0], [.9, 0], [.9, 1], [.1, 1]]
    with pytest.raises(ValueError, match="shared.*outline"):
        load(tmp_path, data)
