"""A single threaded sling must not become two fictional loops."""
import copy
import json
from pathlib import Path

import pytest

from conftest import load_board_catalog_module


def single_loop():
    root = Path(__file__).resolve().parents[3]
    setup = json.loads((root / "Hangboards/lattice-mini-bar/assets/suspension.json").read_text())["suspension"]
    setup["passages"]["right"] = []
    setup["branches"] = setup["branches"][:1]
    ids = {p["id"] for p in setup["passages"]["left"]}
    setup["internalLoop"]["windingByPassageID"] = {
        k: v for k, v in setup["internalLoop"]["windingByPassageID"].items() if k in ids
    }
    setup["internalLoop"]["channelLengthByBranchID"] = {
        setup["branches"][0]["id"]: next(iter(setup["internalLoop"]["channelLengthByBranchID"].values()))
    }
    for pose in setup["canonicalPoses"].values():
        pose["cordContactPoints"] = {k: v for k, v in pose["cordContactPoints"].items() if k in ids}
    return setup


@pytest.mark.parametrize("mouth_role", ["body", "attachment", "contact", None])
def test_one_cached_connected_loop_preserves_two_visible_legs(mouth_role):
    module = load_board_catalog_module()
    setup = single_loop()
    profile = module._load_model_suspension(setup, "suspension")
    assert len(profile.branches) == 1
    assert len(profile.passages.left) == 2
    assert profile.passages.right == ()
    assert [passage.node_id for passage in profile.passages.left] == [
        mouth["nodeID"] for mouth in setup["passages"]["left"]
    ]
    root = Path(__file__).resolve().parents[3]
    bounds = json.loads((root / "Hangboards/lattice-mini-bar/assets/primary.model.json").read_text())["modelBounds"]
    nodes = {passage.node_id: "body" for passage in profile.passages.left}
    mouth_node_id = profile.passages.left[0].node_id
    if mouth_role is None:
        del nodes[mouth_node_id]
    else:
        nodes[mouth_node_id] = mouth_role
    def validate_binding():
        module._validate_model_suspension(
            profile,
            model_bounds=(bounds["min"], bounds["max"]),
            nodes=nodes,
            position_ids=set(profile.canonical_poses),
        )
    if mouth_role in {"body", "attachment"}:
        validate_binding()
        assert nodes[mouth_node_id] == mouth_role
    else:
        with pytest.raises(ValueError, match="passage node must be a body or attachment"):
            validate_binding()


@pytest.mark.parametrize("mutation", ["no-loop", "uncached", "partial-pair", "extra-branch"])
def test_one_loop_extension_rejects_incomplete_or_exterior_topology(mutation):
    module = load_board_catalog_module()
    setup = copy.deepcopy(single_loop())
    if mutation == "no-loop":
        del setup["internalLoop"]
    elif mutation == "uncached":
        for pose in setup["canonicalPoses"].values():
            del pose["cordContactPoints"]
    elif mutation == "partial-pair":
        setup["passages"]["left"].pop()
    else:
        setup["branches"].append(copy.deepcopy(setup["branches"][0]))
    with pytest.raises(ValueError):
        module._load_model_suspension(setup, "suspension")
