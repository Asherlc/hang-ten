"""One physical top surface participates in jug and opposing pinch grips."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contact_model_descriptor import ModelDescriptorV1, NodeBinding, compile_descriptor


def fixture():
    vertices = {
        "body": [(-.065, -.03, -.02), (.065, .03, .02)],
        "bottom": [(-.047, -.03, -.02), (.047, -.027, .02)],
        "top": [(-.047, .027, -.02), (.047, .03, .02)],
    }
    nodes = [NodeBinding("body", "body"), NodeBinding("bottom", "contact", "pinch")]
    return vertices, nodes


def shared_descriptor():
    vertices, nodes = fixture()
    nodes.append(NodeBinding("top", "contact", "jug", additional_contact_ids=("pinch",)))
    return compile_descriptor(b"one top mesh", nodes, vertices, frozenset({"jug", "pinch"}))


def test_shared_top_extends_pinch_to_both_bearing_planes_without_duplicate_node():
    result = shared_descriptor()
    assert len(result.nodes) == 3
    assert result.contacts["pinch"].node_ids == ("bottom", "top")
    assert result.contacts["pinch"].face_plane_aabb.min[1] == 0
    assert result.contacts["pinch"].face_plane_aabb.max[1] == 1
    assert result.contacts["jug"].node_ids == ("top",)
    assert result.contacts["jug"].face_plane_aabb.min[1] == .95
    payload = result.to_json()
    assert payload["nodes"][-1] == {
        "nodeID": "top", "role": "contact", "contactID": "jug", "additionalContactIDs": ["pinch"]
    }
    assert ModelDescriptorV1.from_json(payload).to_json() == payload


@pytest.mark.parametrize("extra", [[], None, "pinch", [""], [1], ["pinch", "pinch"], ["jug"], ["z", "a"]])
def test_closed_descriptor_rejects_malformed_additional_membership(extra):
    vertices, nodes = fixture()
    nodes.append(NodeBinding("top", "contact", "jug"))
    payload = compile_descriptor(b"one top mesh", nodes, vertices, frozenset({"jug", "pinch"})).to_json()
    payload["nodes"][-1]["additionalContactIDs"] = extra
    with pytest.raises(ValueError):
        ModelDescriptorV1.from_json(payload)


@pytest.mark.parametrize("role", ["body", "attachment"])
def test_non_contact_cannot_share_membership(role):
    vertices, nodes = fixture()
    nodes.append(NodeBinding("top", "contact", "jug"))
    payload = compile_descriptor(b"mesh", nodes, vertices, frozenset({"jug", "pinch"})).to_json()
    payload["nodes"][0]["role"] = role
    payload["nodes"][0]["additionalContactIDs"] = ["pinch"]
    with pytest.raises(ValueError):
        ModelDescriptorV1.from_json(payload)


def test_unknown_additional_identity_and_stale_union_are_rejected():
    vertices, nodes = fixture()
    nodes.append(NodeBinding("top", "contact", "jug", additional_contact_ids=("unknown",)))
    with pytest.raises(ValueError, match="logical contact"):
        compile_descriptor(b"mesh", nodes, vertices, frozenset({"jug", "pinch"}))
    payload = shared_descriptor().to_json()
    payload["contacts"]["pinch"]["nodeIDs"] = ["bottom"]
    with pytest.raises(ValueError, match="exactly match"):
        ModelDescriptorV1.from_json(payload)


def test_old_outline_cannot_hide_added_surface_from_union_bounds():
    vertices, nodes = fixture()
    nodes.append(NodeBinding("top", "contact", "jug", additional_contact_ids=("pinch",)))
    with pytest.raises(ValueError, match="shared.*outline"):
        compile_descriptor(b"mesh", nodes, vertices, frozenset({"jug", "pinch"}),
                           {"pinch": [(-.04, -.03), (.04, -.03), (.04, -.027)]})


def test_closed_descriptor_rejects_outline_on_shared_membership():
    payload = shared_descriptor().to_json()
    payload["contacts"]["pinch"]["outline"] = [[.138461538, 0], [.861538462, 0], [.861538462, 1], [.138461538, 1]]
    with pytest.raises(ValueError, match="shared.*outline"):
        ModelDescriptorV1.from_json(payload)


@pytest.mark.parametrize("extras", [("pinch", "pinch"), ("jug",), ("z", "a"), "pinch", None, (1,)])
def test_compiler_api_rejects_invalid_memberships(extras):
    vertices, nodes = fixture()
    nodes.append(NodeBinding("top", "contact", "jug", additional_contact_ids=extras))
    with pytest.raises(ValueError):
        compile_descriptor(b"mesh", nodes, vertices, frozenset({"jug", "pinch"}))


def test_existing_catalog_descriptors_roundtrip_without_new_fields():
    root = Path(__file__).resolve().parents[3]
    checked = 0
    for path in sorted((root / "Hangboards").glob("*/assets/*.model.json")):
        payload = json.loads(path.read_text())
        if payload["schemaVersion"] != 1:
            continue
        assert ModelDescriptorV1.from_json(copy.deepcopy(payload)).to_json() == payload
        checked += 1
    assert checked > 40
