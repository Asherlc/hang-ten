"""Native pose-specific terminal stations preserve geometry and solver isolation."""
import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Tools/HangboardCAD"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Tools/HangboardPackages/src"))
from hangboard_packages import cad_source
from native_cord_routes import solve_native_routes, checked_clearance, length


def loop_fixture(accelerated=True):
    mesh = trimesh.creation.box(extents=[.1, .06, .06])
    pose = {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1]}
    default = {"loop": {"points": [[0, -.033, -.033], [0, -.033, .033]],
                        "planeNormal": [1, 0, 0]}}
    override = copy.deepcopy(default)
    override["loop"]["points"] = [[.02, -.033, -.033], [.02, -.033, .033]]
    data = {"suspension": {
        "type": "cadRoutedCord",
        "strands": [{"id": "loop", "kind": "loop", "radius": .002, "restLength": .5}],
        "anchor": {"offsetFromBoardBounds": [0, .08, 0]},
        "canonicalPoses": {key: copy.deepcopy(pose) for key in ("default", "shifted")}},
        "ropeSolver": {"method": "nativeRoutes", "clearance": .0002,
            "sectionPlane": "anchor", "terminalsByStrandID": default,
            "terminalsByPoseID": {"shifted": override}}}
    if accelerated:
        data["ropeSolver"]["pathSearch"] = "aStar"
    descriptor = {"modelBounds": {"min": mesh.bounds[0].tolist(), "max": mesh.bounds[1].tolist()}}
    return mesh, data, descriptor


def merge_fixture(tmp_path, data):
    (tmp_path / "assets").mkdir(exist_ok=True)
    (tmp_path / "assets/primary.model.json").write_text(json.dumps({"modelSHA256": "a" * 64}))
    board = {"presentations": [{"id": "main", "media": {
        "type": "model", "descriptorPath": "assets/primary.model.json"}}]}
    sidecar = {"schemaVersion": 1, "presentationID": "main", "modelSHA256": "a" * 64, **data}
    (tmp_path / "suspension.json").write_text(json.dumps(sidecar))
    return cad_source.merge_suspension_sidecar(board, tmp_path)


def test_pose_terminals_are_authoring_only_and_merge_without_input_mutation(tmp_path):
    _, data, _ = loop_fixture()
    before = copy.deepcopy(data)
    merged = merge_fixture(tmp_path, data)
    assert merged["presentations"][0]["media"]["suspension"] == data["suspension"]
    assert data == before
    rendered = cad_source.render_board(merged).decode()
    assert "ropeSolver" not in rendered and "terminalsByPoseID" not in rendered


@pytest.mark.parametrize("case", [
    "unknown_pose", "unknown_strand", "missing_strand", "wrong_arity", "bad_vector_arity",
    "nonfinite_point", "boolean_point", "zero_normal", "nonfinite_normal", "bad_normal_arity",
    "zero_plane_axis", "bad_mouth_axis", "incompatible_mouth_axis", "unknown_station_field",
    "not_pose_map", "not_station_map",
])
def test_invalid_pose_station_maps_are_rejected(tmp_path, case):
    _, data, _ = loop_fixture()
    overrides = data["ropeSolver"]["terminalsByPoseID"]
    stations = overrides["shifted"]
    entry = stations["loop"]
    if case == "unknown_pose": overrides["absent"] = overrides.pop("shifted")
    elif case == "unknown_strand": stations["absent"] = stations.pop("loop")
    elif case == "missing_strand": stations.clear()
    elif case == "wrong_arity": entry["points"] = entry["points"][:1]
    elif case == "bad_vector_arity": entry["points"][0] = [0, 0]
    elif case == "nonfinite_point": entry["points"][0][0] = float("inf")
    elif case == "boolean_point": entry["points"][0][0] = True
    elif case == "zero_normal": entry["planeNormal"] = [0, 0, 0]
    elif case == "nonfinite_normal": entry["planeNormal"] = [float("inf"), 0, 0]
    elif case == "bad_normal_arity": entry["planeNormal"] = [1, 0]
    elif case == "zero_plane_axis": entry["planeAxis"] = [0, 0, 0]
    elif case == "bad_mouth_axis": entry["mouthAxis"] = [True, 0, 0]
    elif case == "incompatible_mouth_axis": entry["mouthAxis"] = [0, 0, 1]
    elif case == "unknown_station_field": entry["inventedGuide"] = [0, 0, 0]
    elif case == "not_pose_map": data["ropeSolver"]["terminalsByPoseID"] = []
    elif case == "not_station_map": overrides["shifted"] = []
    with pytest.raises(cad_source.ManifestError):
        merge_fixture(tmp_path, data)


@pytest.mark.parametrize("accelerated", [False, True], ids=["dijkstra", "astar"])
def test_same_frame_distinct_stations_solve_closed_solid_loops_independently(accelerated):
    mesh, data, descriptor = loop_fixture(accelerated)
    before = copy.deepcopy(data)
    expected = {}
    # Baseline oracle uses existing one-pose/global-station behavior, without
    # the extension, so this tests isolation independently of its implementation.
    for pose_id, pose in data["suspension"]["canonicalPoses"].items():
        single = copy.deepcopy(data)
        overrides = single["ropeSolver"].pop("terminalsByPoseID")
        single["ropeSolver"]["terminalsByStrandID"] = overrides.get(
            pose_id, single["ropeSolver"]["terminalsByStrandID"])
        single["suspension"]["canonicalPoses"] = {pose_id: pose}
        expected.update(solve_native_routes(mesh, single, descriptor))
    actual = solve_native_routes(mesh, data, descriptor)
    assert actual == expected
    assert actual["default"]["routes"] != actual["shifted"]["routes"]
    assert data == before
    for pose_id, result in actual.items():
        # Independently reconstruct the closed runtime loop including fixed support.
        support = np.array([0, .11 - result["height"], 0])
        route = np.asarray(result["routes"]["loop"])
        path = np.vstack([support, route, support])
        assert checked_clearance(mesh, path, .002) >= .002 - 1e-5
        assert length(path) == pytest.approx(.5, abs=5e-7)
        assert result["lengthRatios"]["loop"] == pytest.approx(1, abs=1e-6)
        stations = data["ropeSolver"]["terminalsByPoseID"].get(
            pose_id, data["ropeSolver"]["terminalsByStrandID"])["loop"]["points"]
        for station in stations:
            assert any(np.linalg.norm(point - station) < 1e-9 for point in route)


def test_no_override_preserves_legacy_solver_result_exactly():
    mesh, data, descriptor = loop_fixture()
    data["ropeSolver"].pop("terminalsByPoseID")
    reference = solve_native_routes(mesh, data, descriptor)
    explicit = copy.deepcopy(data)
    explicit["ropeSolver"]["terminalsByPoseID"] = {
        "shifted": copy.deepcopy(data["ropeSolver"]["terminalsByStrandID"])}
    assert solve_native_routes(mesh, explicit, descriptor) == reference


def test_pose_terminals_reject_empty_override_map(tmp_path):
    _, data, _ = loop_fixture()
    data["ropeSolver"]["terminalsByPoseID"] = {}
    with pytest.raises(cad_source.ManifestError, match="canonical poses"):
        merge_fixture(tmp_path, data)


def test_pose_terminals_reject_groove_guide_combination(tmp_path):
    mesh, data, descriptor = loop_fixture()
    data["ropeSolver"]["grooveGuides"] = {}
    with pytest.raises(cad_source.ManifestError, match="grooveGuides"):
        merge_fixture(tmp_path, data)
    with pytest.raises(ValueError, match="grooveGuides"):
        solve_native_routes(mesh, data, descriptor)
