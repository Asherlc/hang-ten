"""Exact-snapshot integration seam contracts, independent of actual CAD exports."""
import copy
import sys
import types
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Tools/HangboardPackages/src"))
import native_cord_routes as routes
from test_native_pose_terminals import loop_fixture

@pytest.mark.parametrize("has_metadata", [False, True])
def test_pose_terminal_recursion_preserves_optional_source_metadata(monkeypatch, has_metadata):
    mesh, data, descriptor = loop_fixture()
    before = copy.deepcopy(data)
    metadata = {"sourceSHA256": "a" * 64, "nativeFeatures": {}} if has_metadata else None
    actual_solver = routes.solve_native_routes
    calls = []
    def child(child_mesh, child_data, child_descriptor, source_metadata=None):
        calls.append((child_mesh, child_data, child_descriptor, source_metadata))
        assert "terminalsByPoseID" not in child_data["ropeSolver"]
        assert len(child_data["suspension"]["canonicalPoses"]) == 1
        return {next(iter(child_data["suspension"]["canonicalPoses"])): {"sentinel": len(calls)}}
    monkeypatch.setattr(routes, "solve_native_routes", child)
    result = actual_solver(mesh, data, descriptor, source_metadata=metadata)
    assert set(result) == {"default", "shifted"}
    assert len(calls) == 2 and all(c[0] is mesh and c[2] is descriptor and c[3] is metadata for c in calls)
    assert calls[0][1]["ropeSolver"]["terminalsByStrandID"] == data["ropeSolver"]["terminalsByStrandID"]
    assert calls[1][1]["ropeSolver"]["terminalsByStrandID"] == data["ropeSolver"]["terminalsByPoseID"]["shifted"]
    assert data == before


def test_groove_dispatch_forwards_exact_source_metadata_without_mutation(monkeypatch):
    mesh, data, descriptor = loop_fixture()
    data["ropeSolver"].pop("terminalsByPoseID")
    data["ropeSolver"]["grooveGuides"] = {"testSentinel": True}
    before = copy.deepcopy(data)
    metadata = {"sourceSHA256": "a" * 64}
    output = {"guide": "sentinel"}
    calls = []
    def guided(*args):
        calls.append(args)
        return output
    monkeypatch.setitem(sys.modules, "native_cord_guides", types.SimpleNamespace(solve_groove_guided_routes=guided))
    assert routes.solve_native_routes(mesh, data, descriptor, source_metadata=metadata) is output
    assert len(calls) == 1
    assert all(a is b for a, b in zip(calls[0], (mesh, data, descriptor, metadata)))
    assert data == before


def test_combined_fields_reject_before_either_dispatch(monkeypatch):
    mesh, data, descriptor = loop_fixture()
    data["ropeSolver"]["grooveGuides"] = {"testSentinel": True}
    before = copy.deepcopy(data)
    def forbidden(*args, **kwargs):
        pytest.fail("combined fields reached groove dispatch")
    monkeypatch.setitem(sys.modules, "native_cord_guides", types.SimpleNamespace(solve_groove_guided_routes=forbidden))
    with pytest.raises(ValueError, match="cannot be combined with grooveGuides"):
        routes.solve_native_routes(mesh, data, descriptor, source_metadata={"sourceSHA256": "a" * 64})
    assert data == before
