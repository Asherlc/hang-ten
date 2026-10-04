"""Explicit CAD face membership and union depth for an opposing pinch."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compile_board
import contract


def region(key, zmin, zmax, *, additional=None, axis="y"):
    box = SimpleNamespace(XMin=-47., XMax=47., XLength=94., YMin=-20., YMax=20.,
                          YLength=40., ZMin=zmin, ZMax=zmax, ZLength=zmax-zmin)
    obj = SimpleNamespace(Name=key, NodeID=key, NodeRole="contact", ContactID=key,
                          PropertiesList=["ContactID", "HangTenDepthAxis"],
                          HangTenDepthAxis=axis, Shape=SimpleNamespace(BoundBox=box))
    if additional is not None:
        obj.AdditionalContactIDs = additional
        obj.PropertiesList.append("AdditionalContactIDs")
        obj.getTypeIdOfProperty = lambda name: "App::PropertyStringList"
    return obj


def test_native_membership_survives_specs_and_measures_opposing_z_span():
    bottom = region("pinch", -30., -27., axis="z")
    top = region("jug", 27., 30., additional=["pinch"])
    spec = compile_board._node_specification(top, 1)
    assert spec == {"id": "jug", "role": "contact", "contact": "jug", "additionalContactIDs": ["pinch"]}
    board = {"schemaVersion": 3, "id": "test", "contacts": [{"id": "jug"}, {"id": "pinch"}]}
    contract.validate_bindings([{"id": "body", "role": "body"}, spec,
                                compile_board._node_specification(bottom, 1)], board, 1, [])
    assert compile_board._validate_published_depths(
        [top, bottom], {"jug": 40, "pinch": 60}, 1, .05,
        {"x": 130, "y": 40, "z": 60}) == {"jug": 40, "pinch": 60}


def test_missing_opposing_face_still_fails_published_sixty_mm_gate():
    with pytest.raises(compile_board.BuildError, match="published depth"):
        compile_board._validate_published_depths([region("pinch", -30, -27, axis="z")],
                                               {"pinch": 60}, 1, .05, {"z": 60})


@pytest.mark.parametrize("extras", [[], ["jug"], ["pinch", "pinch"], ["z", "a"], "pinch", None, [1]])
def test_source_binding_rejects_malformed_additional_membership(extras):
    board = {"schemaVersion": 3, "id": "test", "contacts": [{"id": "jug"}, {"id": "pinch"}]}
    nodes = [{"id": "body", "role": "body"}, {"id": "bottom", "role": "contact", "contact": "pinch"},
             {"id": "top", "role": "contact", "contact": "jug", "additionalContactIDs": extras}]
    with pytest.raises(ValueError):
        contract.validate_bindings(nodes, board, 1, [])


def test_native_property_cannot_be_ignored_on_body_or_reusable_source():
    top = region("jug", 27, 30, additional=["pinch"])
    top.NodeRole = "body"
    with pytest.raises(compile_board.BuildError):
        compile_board._node_specification(top, 1)
    top.NodeRole = "contact"
    with pytest.raises(compile_board.BuildError):
        compile_board._node_specification(top, 2)


def test_native_additional_ids_require_string_list_property():
    top = region("jug", 27, 30, additional=["pinch"])
    top.getTypeIdOfProperty = lambda name: "App::PropertyString"
    with pytest.raises(compile_board.BuildError, match="PropertyStringList"):
        compile_board._node_specification(top, 1)


def test_conflicting_primary_axis_cannot_choose_arbitrary_depth():
    first = region("pinch", -30, -27, axis="z")
    second = region("pinch", -30, -27, axis="x")
    top = region("jug", 27, 30, additional=["pinch"])
    with pytest.raises(compile_board.BuildError, match="conflicting primary"):
        compile_board._validate_published_depths([first, second, top], {"pinch": 60}, 1, .05)


def test_native_shared_depth_needs_primary_axis_authority():
    top = region("jug", 27, 30, additional=["pinch"])
    with pytest.raises(compile_board.BuildError, match="primary contact"):
        compile_board._validate_published_depths([top], {"jug": 40, "pinch": 60}, 1, .05)


def test_native_shared_depth_measures_all_members_independent_of_order():
    bottom = region("pinch", -30, -27, axis="z")
    top = region("jug", 27, 30, additional=["pinch"])
    for objects in ([bottom, top], [top, bottom]):
        assert compile_board._validate_published_depths(objects, {"jug": 40, "pinch": 60}, 1, .05) == {"jug": 40, "pinch": 60}


@pytest.mark.parametrize("shared_first", [False, True])
def test_unrelated_sharing_cannot_make_separate_twenty_mm_edges_pass_sixty(shared_first):
    edges = [region("edge", 0, 20, axis="z"), region("edge", 40, 60, axis="z")]
    shared = [region("pinch", -30, -27, axis="z"),
              region("jug", 27, 30, additional=["pinch"])]
    declared = {"edge": 60, "pinch": 60, "jug": 40}
    with pytest.raises(compile_board.BuildError, match="edge region depth 20.000"):
        compile_board._validate_published_depths(edges, declared, 1, .05)
    objects = shared + edges if shared_first else edges + shared
    with pytest.raises(compile_board.BuildError, match="edge region depth 20.000"):
        compile_board._validate_published_depths(objects, declared, 1, .05)


def test_unrelated_primary_axes_keep_their_independent_legacy_checks():
    edges = [region("edge", -60, -20, axis="z"), region("edge", 20, 60, axis="y")]
    assert compile_board._validate_published_depths(edges, {"edge": 40}, 1, .05) == {"edge": 40}
    shared = [region("pinch", -30, -27, axis="z"),
              region("jug", 27, 30, additional=["pinch"])]
    assert compile_board._validate_published_depths(
        edges + shared, {"edge": 40, "pinch": 60, "jug": 40}, 1, .05
    ) == {"edge": 40, "pinch": 60, "jug": 40}


def test_shared_primary_with_only_one_witness_still_fails_closed():
    bottom = region("pinch", -30, -27, axis="z")
    bottom.PropertiesList.append("HangTenGripDepthStart")
    bottom.HangTenGripDepthStart = SimpleNamespace(x=0, y=0, z=-30)
    top = region("jug", 27, 30, additional=["pinch"])
    with pytest.raises(compile_board.BuildError, match="requires both native lip and floor"):
        compile_board._validate_published_depths([bottom, top], {"pinch": 60}, 1, .05)
