"""Runtime rope inputs bind geometry, continuous topology and actual thickness."""
from copy import deepcopy
import json
import pytest

from hangboard_packages.rope_physics import derive_radius, validate_rope_physics, load_rope_physics

MODEL_SHA = "a" * 64


def physics_fixture():
    vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
    triangles = [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]
    portals = [{"id": name, "center": [0, 0, z], "normal": [0, 0, sign],
                "boundary": [[-.012, -.013, z], [.012, -.013, z],
                             [.012, .013, z], [-.012, .013, z]]}
               for name, z, sign in [("front", .045, 1), ("back", -.045, -1)]]
    nodes = [{"id": "start", "kind": "support", "point": [0, .3, 0]},
             {"id": "enter", "kind": "portal", "portalID": "front"},
             {"id": "exit", "kind": "portal", "portalID": "back"},
             {"id": "end", "kind": "support", "point": [0, .3, 0]}]
    edges = [{"from": "start", "to": "enter", "kind": "free", "winding": "clockwise"},
             {"from": "enter", "to": "exit", "kind": "channel", "channelID": "central"},
             {"from": "exit", "to": "end", "kind": "free", "winding": "counterclockwise"}]
    rope = {"id": "sling", "baselineRadius": .002, "thicknessScale": 3,
            "radius": .006, "restLength": .55, "lengthProvenance": "displayEstimate: loop length",
            "linearMass": {"value": .01, "provenance": "displayEstimate: kg/m"},
            "nodes": nodes, "edges": edges}
    return {"schemaVersion": 1, "sourceSHA256": "b" * 64, "modelSHA256": MODEL_SHA,
            "coordinateSystem": "hang-ten-board-v1",
            "collision": {"vertices": vertices, "triangles": triangles},
            "portals": portals,
            "channels": [{"id": "central", "portalIDs": ["front", "back"],
                          "spine": [[0, 0, .045], [0, 0, -.045]],
                          "vertices": vertices, "triangles": triangles}],
            "profiles": [{"id": "front", "presentationID": "front",
                          "boardMass": {"value": 1, "provenance": "displayEstimate: kg"},
                          "ropes": [rope]}]}


def test_valid_continuous_loop_and_repeatable_thickness():
    document = physics_fixture()
    assert validate_rope_physics(document, MODEL_SHA) == document
    assert derive_radius(.002, 3) == .006
    assert derive_radius(.002, 3) == derive_radius(.002, 3)


def test_operator_selected_seven_mm_diameter_is_not_forced_to_threefold():
    document = physics_fixture()
    rope = document["profiles"][0]["ropes"][0]
    rope.update(thicknessScale=1.75, radius=.0035)
    assert validate_rope_physics(document, MODEL_SHA) == document
    assert 2 * derive_radius(.002, 1.75) == .007


@pytest.mark.parametrize("baseline,scale", [(0, 3), (-1, 3), (.002, 0), (True, 3), (float("nan"), 3), (.002, float("inf"))])
def test_invalid_thickness(baseline, scale):
    with pytest.raises(ValueError):
        derive_radius(baseline, scale)


@pytest.mark.parametrize("mutation,match", [
    (lambda d: d.update(modelSHA256="c" * 64), "hash"),
    (lambda d: d.update(coordinateSystem="native-mm"), "coordinate"),
    (lambda d: d.update(unrecognized=True), "member"),
    (lambda d: d["profiles"][0]["boardMass"].pop("provenance"), "provenance|member"),
    (lambda d: d["profiles"][0]["ropes"][0].update(restLength=0), "length"),
    (lambda d: d["profiles"][0]["ropes"][0].update(radius=.002), "radius"),
    (lambda d: d["profiles"][0]["ropes"][0].pop("lengthProvenance"), "member|provenance"),
    (lambda d: d["profiles"][0]["ropes"][0]["nodes"][2].update(id="enter"), "duplicate"),
    (lambda d: d["profiles"][0]["ropes"][0]["edges"][0].update(to="missing"), "graph"),
    (lambda d: d["profiles"][0]["ropes"][0]["edges"][1].update(channelID="missing"), "channel"),
    (lambda d: d["portals"].append(deepcopy(d["portals"][0])), "duplicate"),
    (lambda d: d["portals"][0].update(normal=[0, 0, 0]), "normal"),
    (lambda d: d["collision"]["vertices"][0].__setitem__(0, float("nan")), "finite"),
    (lambda d: d["collision"]["triangles"][0].__setitem__(0, 42), "triangle"),
    (lambda d: d["profiles"][0]["ropes"][0]["nodes"][1].update(point=[0, 0, .045]), "member"),
    (lambda d: d["collision"]["triangles"][0].__setitem__(0, {}), "triangle"),
    (lambda d: d["channels"][0]["portalIDs"].__setitem__(0, []), "identifier"),
    (lambda d: d["collision"]["triangles"][0].reverse(), "winding"),
])
def test_invalid_descriptor_fails_closed(mutation, match):
    document = physics_fixture()
    mutation(document)
    with pytest.raises(ValueError, match=match):
        validate_rope_physics(document, MODEL_SHA)


def test_thick_rope_fit_does_not_enlarge_a_narrow_opening():
    document = physics_fixture()
    document["portals"][0]["boundary"] = [[x / 10, y / 10, z]
                                                for x, y, z in document["portals"][0]["boundary"]]
    original = deepcopy(document)
    with pytest.raises(ValueError, match="fit"):
        validate_rope_physics(document, MODEL_SHA)
    assert document == original


def test_regular_bound_file_and_duplicate_keys(tmp_path):
    document = physics_fixture()
    path = tmp_path / "fixture.physics.json"
    path.write_text(json.dumps(document))
    assert load_rope_physics(path, MODEL_SHA) == document
    path.write_text('{"schemaVersion":1,"schemaVersion":1}')
    with pytest.raises(ValueError, match="duplicate"):
        load_rope_physics(path, MODEL_SHA)


def test_missing_or_symlink_descriptor_fails(tmp_path):
    target = tmp_path / "fixture.physics.json"
    with pytest.raises(ValueError, match="regular"):
        load_rope_physics(target, MODEL_SHA)
    target.write_text(json.dumps(physics_fixture()))
    link = tmp_path / "link.physics.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="regular"):
        load_rope_physics(link, MODEL_SHA)
