from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_exterior_wrap_uses_the_closed_solid_and_clearance():
    from native_cord_routes import NativeSection, checked_clearance
    mesh = trimesh.creation.box(extents=[.10, .06, .06])
    terminal = np.array([0, -.034, .034])
    anchor = np.array([0, .3, 0])
    section = NativeSection(mesh, terminal, [1,0,0], .002, .0002)
    path = section.route(anchor, terminal)
    assert len(path) >= 3
    assert np.allclose(path[0], anchor) and np.allclose(path[-1], terminal)
    assert checked_clearance(mesh, path, .002) >= .002 - 1e-5


def test_a_terminal_inside_wood_cannot_be_promoted_to_a_cord_route():
    from native_cord_routes import NativeSection
    mesh = trimesh.creation.box(extents=[.10, .06, .06])
    section = NativeSection(mesh, [0,0,0], [1,0,0], .002, .0002)
    with pytest.raises(ValueError, match="inside"):
        section.route(np.array([0,.3,0]), np.array([0,0,0]))


def test_clearance_certifies_thin_obstacles_between_sample_locations():
    from native_cord_routes import checked_clearance
    mesh = trimesh.creation.box(extents=[.00002, .01, .01])
    mesh.apply_translation([0, .005, .005])
    path = np.array([[-.00025, -.00069, -.00069], [.00025, -.00069, -.00069]])
    endpoint_clearance = -trimesh.proximity.signed_distance(mesh, path)
    assert endpoint_clearance.min() > .001
    with pytest.raises(ValueError, match="collision"):
        checked_clearance(mesh, path, .001)


def test_anchor_plane_avoids_the_wider_solid_beyond_a_tapered_end():
    from native_cord_routes import NativeSection, checked_clearance
    # Deliberate analytic section: a narrow end grows into a wider bar.
    mesh = trimesh.creation.revolve(np.array([
        [0, -.05], [.015, -.05], [.03, -.04], [.03, .04], [.015, .05], [0, .05]
    ]), sections=32)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
    terminal, anchor = np.array([-.049, 0, .020]), np.array([.01, .05, 0])
    fixed = NativeSection(mesh, terminal, [1,0,0], .001, .0002)
    with pytest.raises(ValueError, match="collision"):
        checked_clearance(mesh, fixed.route(anchor, terminal), .001)
    section = NativeSection.for_span(mesh, anchor, terminal, [1,0,0], .001, .0002)
    path = section.route(anchor, terminal)
    assert checked_clearance(mesh, path, .001) >= .001 - 1e-5
    assert abs(np.dot(anchor - section.origin, section.normal)) < 1e-10


def test_source_backed_mouth_axis_does_not_bypass_full_solid_clearance():
    from native_cord_routes import NativeSection, checked_clearance
    mesh = trimesh.creation.revolve(np.array([
        [0, -.05], [.015, -.05], [.03, -.04], [.03, .04], [.015, .05], [0, .05]
    ]), sections=32)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
    terminal, anchor = np.array([-.049, 0, .019]), np.array([0, .3, 0])
    section = NativeSection.for_span(mesh, anchor, terminal, [1,0,0], .001, .0005, plane_axis=[0,0,1])
    assert abs(np.dot(section.normal, [0,0,1])) < 1e-10
    assert abs(np.dot(anchor - terminal, section.normal)) < 1e-10
    with pytest.raises(ValueError, match="collision"):
        checked_clearance(mesh, section.route(anchor, terminal), .001)


def test_independent_loop_legs_cannot_retrace_each_other():
    from native_cord_routes import solve_native_routes
    mesh = trimesh.creation.box(extents=[.1, .06, .06])
    data = {"suspension": {
        "strands": [{"id": "loop", "kind": "loop", "restLength": .4, "radius": .002}],
        "anchor": {"offsetFromBoardBounds": [0, .1, 0]},
        "canonicalPoses": {"upright": {"translation": [0,0,0], "rotation": [0,0,0,1]}}},
        "ropeSolver": {"clearance": .0002, "terminalsByStrandID": {"loop": {
            "points": [[0,.01,.034], [0,-.01,.034]], "planeNormal": [1,0,0]}}}}
    with pytest.raises(ValueError, match="retrace|intersect"):
        solve_native_routes(mesh, data, {"modelBounds": {"min": [-.05,-.03,-.03], "max": [.05,.03,.03]}})


def test_native_bore_collar_preserves_actual_mouth_and_certifies_rounded_route():
    from native_cord_routes import native_mouth_collar, solve_native_routes, checked_clearance
    # Analytic through-bore: the exit direction is evidence, not a drawn route.
    mesh = trimesh.creation.annulus(r_min=.003, r_max=.02, height=.01, sections=48)
    mouth = np.array([0, 0, .005])
    exterior = native_mouth_collar(mesh, mouth, [0,0,1], .002, .0005)
    assert np.allclose(exterior, [0,0,.0075])
    data = {"suspension": {
        "strands": [{"id":"lead", "kind":"lead", "restLength":.15, "radius":.002}],
        "anchor":{"offsetFromBoardBounds":[.02,.025,.035]},
        "canonicalPoses":{"upright":{"translation":[0,0,0], "rotation":[0,0,0,1]}}},
        "ropeSolver":{"sectionPlane":"anchor", "clearance":.0005,
            "terminalsByStrandID":{"lead":{"points":[mouth.tolist()],
                "planeNormal":[1,0,0], "mouthAxis":[0,0,1]}}}}
    descriptor = {"modelBounds":{"min":mesh.bounds[0].tolist(),"max":mesh.bounds[1].tolist()}}
    result = solve_native_routes(mesh, data, descriptor)["upright"]
    route = np.asarray(result["routes"]["lead"])
    assert np.array_equal(route[-1], mouth)
    assert np.allclose(route[-2], exterior)
    support = np.array([.02,.045-result["height"],.035])
    assert checked_clearance(mesh, np.vstack([support,route]), .002) >= .002-1e-5


def test_mouth_axis_cannot_route_a_collar_through_wood():
    from native_cord_routes import native_mouth_collar
    mesh = trimesh.creation.annulus(r_min=.003, r_max=.02, height=.01, sections=48)
    with pytest.raises(ValueError, match="collision"):
        native_mouth_collar(mesh, [0,0,.005], [1,0,0], .002, .0005)
    with pytest.raises(ValueError, match="nonzero"):
        native_mouth_collar(mesh, [0,0,.005], [0,0,0], .002, .0005)


@pytest.mark.parametrize('kind,plane', [('segment','anchor'), ('lead','fixed')])
def test_native_mouth_axis_rejects_incompatible_topology(kind, plane):
    from native_cord_routes import solve_native_routes
    mesh = trimesh.creation.annulus(r_min=.003, r_max=.02, height=.01, sections=24)
    data = {'suspension': {
        'strands': [{'id':'strand', 'kind':kind, 'restLength':.15, 'radius':.002}],
        'anchor': {'offsetFromBoardBounds':[0,.1,0]}, 'canonicalPoses': {}},
        'ropeSolver': {'clearance':.0005, 'sectionPlane':plane,
            'terminalsByStrandID': {'strand': {'points':[[0,0,.005]],
                'mouthAxis':[0,0,1], 'planeNormal':[1,0,0]}}}}
    descriptor = {'modelBounds': {'min':mesh.bounds[0].tolist(), 'max':mesh.bounds[1].tolist()}}
    with pytest.raises(ValueError, match='one lead mouth and an anchor section'):
        solve_native_routes(mesh, data, descriptor)
