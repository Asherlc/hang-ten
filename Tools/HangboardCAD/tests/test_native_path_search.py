"""Opt-in admissible graph search must preserve geometry and default routes."""
from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_cord_routes import NativeSection, checked_clearance, length, solve_native_routes


def test_astar_matches_shortest_route_and_avoids_irrelevant_graph_expansion():
    mesh = trimesh.creation.box(extents=[.10, .06, .06])
    start, finish = np.array([0, .3, 0]), np.array([0, -.034, .034])
    legacy = NativeSection(mesh, finish, [1, 0, 0], .002, .0002)
    expected = legacy.route(start, finish)
    accelerated = NativeSection(mesh, finish, [1, 0, 0], .002, .0002, path_search="aStar")
    actual = accelerated.route(start, finish)
    assert length(actual) == pytest.approx(length(expected), abs=1e-11)
    assert checked_clearance(mesh, actual, .002) >= .002 - 1e-5
    assert len(accelerated.adj) < len(legacy.adj)
    assert np.array_equal(actual[[0, -1]], [start, finish])


def test_astar_symmetric_equal_length_routes_are_deterministic():
    mesh = trimesh.creation.box(extents=[.10, .04, .04])
    start, finish = [0, .1, 0], [0, -.1, 0]
    paths = [NativeSection(mesh, finish, [1, 0, 0], .002, .0002, path_search="aStar").route(start, finish)
             for _ in range(3)]
    assert all(np.array_equal(paths[0], route) for route in paths[1:])
    legacy = NativeSection(mesh, finish, [1, 0, 0], .002, .0002).route(start, finish)
    assert length(paths[0]) == pytest.approx(length(legacy), abs=1e-11)
    assert checked_clearance(mesh, paths[0], .002) >= .002 - 1e-5


def test_astar_tilted_span_preserves_actual_endpoint_weights():
    mesh = trimesh.creation.box(extents=[.10, .06, .06])
    start, finish = np.array([.04, .3, 0]), np.array([-.02, -.034, .034])
    legacy = NativeSection.for_span(mesh, start, finish, [1, 0, 0], .002, .0002)
    accelerated = NativeSection.for_span(mesh, start, finish, [1, 0, 0], .002, .0002, path_search="aStar")
    actual = accelerated.route(start, finish)
    assert length(actual) == pytest.approx(length(legacy.route(start, finish)), abs=1e-11)
    assert np.array_equal(actual[[0, -1]], [start, finish])
    assert np.max(np.abs((actual - accelerated.origin) @ accelerated.normal)) < 1e-12
    assert checked_clearance(mesh, actual, .002) >= .002 - 1e-5


@pytest.mark.parametrize("selector", [None, "dijkstra", "astar", "unknown", 1, [], {}])
def test_public_solver_rejects_invalid_explicit_path_search(selector):
    with pytest.raises(ValueError, match="pathSearch"):
        solve_native_routes(None, {"ropeSolver": {"pathSearch": selector}}, {})


@pytest.mark.parametrize("accelerated", [False, True])
def test_exact_pose_reuse_is_opt_in_and_never_merges_distinct_frames(monkeypatch, accelerated):
    import copy
    import native_cord_routes as native
    mesh = trimesh.creation.box(extents=[.08, .04, .01]); mesh.apply_translation([0, 0, -.03])
    descriptor = {"modelBounds": {"min": mesh.bounds[0].tolist(), "max": mesh.bounds[1].tolist()}}
    original = {"rotation": [0, 0, 0, 1], "translation": [0, -.1, 0]}
    poses = {key: copy.deepcopy(original) for key in ["first", "duplicate", "rotation", "x", "z"]}
    poses["duplicate"].update(translation=[0, -.2, 0], camera={"different": True})
    poses["rotation"]["rotation"] = [0, 0, .1, float(np.sqrt(.99))]
    poses["x"]["translation"][0] = .005
    poses["z"]["translation"][2] = .004
    data = {"suspension": {"strands": [{"id": "lead", "kind": "lead", "radius": .002, "restLength": .25}],
             "anchor": {"offsetFromBoardBounds": [0, .1, .05]}, "canonicalPoses": poses},
            "ropeSolver": {"clearance": .0002, "sectionPlane": "anchor", "terminalsByStrandID": {
                "lead": {"points": [[0, 0, 0]], "planeNormal": [1, 0, 0]}}}}
    if accelerated: data["ropeSolver"]["pathSearch"] = "aStar"
    before = copy.deepcopy(data)
    real_seed = native._solve_native_seed
    solved_ids = []
    def observed_seed(mesh, data, descriptor):
        solved_ids.extend(data["suspension"]["canonicalPoses"])
        return real_seed(mesh, data, descriptor)
    monkeypatch.setattr(native, "_solve_native_seed", observed_seed)
    result = native.solve_native_routes(mesh, data, descriptor)
    assert solved_ids == (["first", "rotation", "x", "z"] if accelerated else list(poses))
    assert result["first"] == result["duplicate"]
    assert all(abs(max(row["lengthRatios"].values()) - 1) < 1e-6 for row in result.values())
    assert data == before
    result["duplicate"]["routes"]["lead"][0][0] = 999
    assert result["first"]["routes"]["lead"][0][0] != 999


@pytest.mark.parametrize("start_x,finish_x", [(.02, -.02), (.02, 0), (0, -.02)])
def test_astar_heuristic_uses_true_off_plane_endpoint_link_lengths(start_x, finish_x):
    mesh = trimesh.creation.box(extents=[.10, .06, .06])
    start, finish = [start_x, .15, 0], [finish_x, -.08, 0]
    legacy = NativeSection(mesh, [0, 0, 0], [1, 0, 0], .002, .0002).route(start, finish)
    accelerated = NativeSection(mesh, [0, 0, 0], [1, 0, 0], .002, .0002, path_search="aStar").route(start, finish)
    assert np.array_equal(accelerated[[0, -1]], [start, finish])
    assert length(accelerated) == pytest.approx(length(legacy), abs=1e-11)
    assert checked_clearance(mesh, accelerated, .002) >= .002 - 1e-5
