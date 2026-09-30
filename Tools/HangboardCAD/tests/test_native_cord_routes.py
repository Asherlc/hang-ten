from pathlib import Path
import json
import sys
import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.mark.parametrize("pose_id", [
    "curved-lip-front", "exterior-jug-back", "left-pocket-vertical", "straight-lip-inverted",
])
def test_captain_dual_cached_leads_enter_the_front_recess_mouth(pose_id):
    # Retained Captain DualP1/title evidence shows each visible lead descending
    # into the FRONT recess opening. A collision-free rear-to-front bore path
    # is geometrically possible, but contradicts that sourced entry direction.
    package = Path(__file__).resolve().parents[3] / "Hangboards/captain-fingerfood-dual"
    data = json.loads((package / "suspension.json").read_text())
    routes = data["suspension"]["canonicalPoses"][pose_id]["wrappedRoutes"]
    for strand_id, x in [("left-lead", -.026), ("right-lead", .026)]:
        route = np.asarray(routes[strand_id])
        mouth = np.array([x, .001, -.005])
        assert np.allclose(route[-1], mouth, atol=1e-9, rtol=0)
        outward_approach = np.dot(route[-2] - mouth, [0, 0, 1])
        assert outward_approach > 1e-5, (
            f"{pose_id}/{strand_id} enters from the rear bore instead of the front recess: "
            f"outward approach {outward_approach * 1000:.6f} mm"
        )


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


def test_occupied_front_collar_blocks_the_other_native_through_bore():
    from shapely.geometry import Point, box
    from shapely.ops import triangulate
    from native_cord_routes import NativeSection, checked_clearance, solve_native_routes
    from hangboard_packages.cord_paths import validate_cord_paths
    # A closed analytic plate with two independent cylindrical daylight holes.
    profile = box(-.06, -.03, .06, .03)
    for x in [-.026, .026]:
        profile = profile.difference(Point(x, 0).buffer(.003, quad_segs=12))
    vertices, faces = [], []
    for triangle in triangulate(profile):
        if profile.covers(triangle):
            face = []
            for point in list(triangle.exterior.coords)[:3]:
                if point not in vertices:
                    vertices.append(point)
                face.append(vertices.index(point))
            faces.append(face)
    mesh = trimesh.creation.extrude_triangulation(vertices, faces, .01)
    mesh.apply_translation([0, 0, -.005])
    assert mesh.is_watertight and mesh.is_winding_consistent
    support, finish = [.10, 0, -.03], [-.026, 0, .0072]
    collar = np.array([[.026, 0, .005], [.026, 0, .0072]])
    section = NativeSection(mesh, finish, [0, 1, 0], .002, .0002)
    shortcut = section.route(support, finish)
    assert checked_clearance(mesh, shortcut, .002) >= .002 - 1e-5
    with pytest.raises(ValueError, match="tubes intersect"):
        validate_cord_paths({"lead": shortcut, "occupied": collar}, {"lead": .002, "occupied": .002})
    section.reserve_tube(*collar, .0042)
    route = section.route(support, finish)
    assert checked_clearance(mesh, route, .002) >= .002 - 1e-5
    validate_cord_paths({"lead": route, "occupied": collar}, {"lead": .002, "occupied": .002})
    # Offset the mouths from the support's body-space Y coordinate, as on
    # DUAL, so the two free-lead planes are distinct rather than retracing.
    mesh.apply_translation([0, .005, 0])
    data = {"suspension": {
        "strands": [{"id": identifier, "kind": "lead", "restLength": .25, "radius": .002}
                    for identifier in ["left", "right"]],
        "anchor": {"offsetFromBoardBounds": [0, .1, -.03]},
        "canonicalPoses": {"vertical": {"rotation": [0, 0, np.sqrt(.5), np.sqrt(.5)], "translation": [0, 0, 0]}}},
        "ropeSolver": {"sectionPlane": "anchor", "clearance": .0002, "terminalsByStrandID": {
            identifier: {"points": [[x, .005, .005]], "mouthAxis": [0, 0, 1],
                         "planeNormal": [0, 1, 0], "planeAxis": [0, 0, 1]}
            for identifier, x in [("left", -.026), ("right", .026)]}}}
    descriptor = {"modelBounds": {"min": mesh.bounds[0].tolist(), "max": mesh.bounds[1].tolist()}}
    result = solve_native_routes(mesh, data, descriptor)["vertical"]
    recovery = result["sectionOrientationRecovery"]
    assert recovery["initialConflict"] == "native cord tubes intersect: left/0, right/1"
    assert recovery["rotationsDegrees"]
    for path in result["routes"].values():
        assert path[-2][2] > path[-1][2]


def test_parallel_offset_collar_uses_its_actual_planar_capsule_section():
    from shapely.geometry import Point
    from native_cord_routes import NativeSection
    section = NativeSection(trimesh.creation.box(extents=[.01, .01, .01]), [0, 0, 0], [0, 1, 0], .001, .0002)
    # A 5 mm capsule 3 mm away intersects the section in a 4 mm capsule.
    section.reserve_tube([.03, .003, -.01], [.03, .003, .01], .005)
    assert section.obstacle.covers(Point(section.to_plane([.0339, 0, 0])))
    assert not section.obstacle.covers(Point(section.to_plane([.0341, 0, 0])))
    # This specifically rejects an inscribed quad_segs=8 cap, whose boundary
    # falls about 19 micrometers inside the exact 4 mm capsule section.
    endpoint = Point(section.to_plane([.03, 0, -.01]))
    assert section.obstacle.boundary.distance(endpoint) >= .004 - 1e-12
    before = section.obstacle
    section.reserve_tube([.05, .006, -.01], [.05, .006, .01], .005)
    assert section.obstacle.equals(before)


def test_oblique_collar_reservation_fails_explicitly_without_projection():
    from native_cord_routes import NativeSection
    section = NativeSection(trimesh.creation.box(extents=[.01, .01, .01]), [0, 0, 0], [0, 1, 0], .001, .0002)
    before = section.obstacle
    with pytest.raises(ValueError, match="parallel to the routing section"):
        section.reserve_tube([.03, -.003, -.01], [.03, .003, .01], .005)
    assert section.obstacle.equals(before)


def test_generated_section_rotation_keeps_the_support_and_derived_collar_endpoint():
    from native_cord_routes import NativeSection
    mesh = trimesh.creation.box(extents=[.1, .06, .06])
    support, collar = np.array([0, .3, 0]), np.array([0, -.034, .034])
    preferred = NativeSection.for_span(mesh, support, collar, [1, 0, 0], .002, .0002, plane_axis=[0, 0, 1])
    rotated = NativeSection.for_span(mesh, support, collar, [1, 0, 0], .002, .0002,
                                    plane_axis=[0, 0, 1], rotation_degrees=17)
    assert abs(np.dot(support - rotated.origin, rotated.normal)) < 1e-12
    assert abs(np.dot(collar - rotated.origin, rotated.normal)) < 1e-12
    assert np.isclose(np.dot(preferred.normal, rotated.normal), np.cos(np.radians(17)))


def _orientation_search_setup():
    return {"suspension": {"strands": [{"id": identifier, "kind": "lead"} for identifier in ["left", "right"]],
                           "canonicalPoses": {"upright": {}}},
            "ropeSolver": {"terminalsByStrandID": {identifier: {"mouthAxis": [0, 0, 1]}
                                                   for identifier in ["left", "right"]}}}


def test_orientation_search_exhausts_its_bound_without_accepting_a_conflict(monkeypatch):
    import native_cord_routes as native
    calls = []
    def conflict(mesh, data, descriptor, rotations=None, allow_collar_reservation=True):
        calls.append(rotations)
        raise ValueError("native cord tubes intersect: left/0, right/1")
    monkeypatch.setattr(native, "_solve_native_routes", conflict)
    with pytest.raises(ValueError, match="exhausted after 30 candidates"):
        native.solve_native_routes(None, _orientation_search_setup(), {})
    assert len(calls) == 31 and calls[0] is None
    assert max(abs(angle) for rotations in calls[1:] for angle in rotations.values()) == 50


@pytest.mark.parametrize("mode", ["valid", "non-conflict", "no-collars"])
def test_orientation_search_preserves_valid_routes_and_unrelated_failures(monkeypatch, mode):
    import native_cord_routes as native
    data = _orientation_search_setup()
    if mode == "no-collars":
        for terminal in data["ropeSolver"]["terminalsByStrandID"].values():
            terminal.clear()
    calls, result = [], {"upright": {"routes": {"left": [[1, 2, 3]]}}}
    error = "native CAD collision: clearance below radius" if mode == "non-conflict" else "native cord tubes intersect: left/0, right/1"
    def preferred(mesh, data, descriptor, rotations=None, allow_collar_reservation=True):
        calls.append(rotations)
        if mode != "valid":
            raise ValueError(error)
        return result
    monkeypatch.setattr(native, "_solve_native_routes", preferred)
    if mode == "valid":
        assert native.solve_native_routes(None, data, {}) == result
    else:
        with pytest.raises(ValueError, match=error):
            native.solve_native_routes(None, data, {})
    assert calls == [None]


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
