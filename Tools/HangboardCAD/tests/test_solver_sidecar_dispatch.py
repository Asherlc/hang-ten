"""Generated-cache dispatch for every retained authoring shape and solver backend."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/HangboardCAD"))
import use_hangboard_packages
from hangboard_packages import cad_source
import solve_threaded_rope as solver
from cad_authoring_fixtures import canonical_pose, write_native_authoring


@pytest.mark.parametrize("layout,native,select", [
    ("single", True, False), ("entries", True, True),
    ("instances", True, False), ("instances", False, False),
    ("instances", False, True),
    ("entry-instances", True, True), ("entry-instances", True, False),
    ("entry-instances", False, True), ("entry-instances", False, False),
    ("entries", True, False),
])
def test_artifact_dispatch_preserves_authoring_and_updates_only_selected_setups(tmp_path, monkeypatch, layout, native, select):
    package = tmp_path / "Hangboards" / "fixture"
    (package / "assets").mkdir(parents=True)
    digest = "a" * 64
    (package / "assets/primary.model.json").write_text(json.dumps({"modelSHA256": digest}))
    def setup():
        result = {"type": "cadRoutedCord" if native else "threadedLoopCord",
                  "canonicalPoses": {"pose": canonical_pose()}}
        if native:
            result["strands"] = [{"id": "strand", "kind": "lead"}]
        else:
            result["passages"] = {
                "left": [{"id": "left-mouth", "pointInModel": [-.04, 0, 0]}],
                "right": [{"id": "right-mouth", "pointInModel": [.04, 0, 0]}],
            }
            result["branches"] = [{"id": "loop", "passageIDs": ["left-mouth", "right-mouth"],
                                    "radius": .0015, "restLength": .5}]
        return result
    data = {"schemaVersion": 1, "presentationID": "view",
            "ropeSolver": {"method": "nativeRoutes", "clearance": .0002,
                "terminalsByStrandID": {"strand": {"points": [[0, 0, 0]], "planeNormal": [1, 0, 0]}}}
                if native else {"sectionPlane": "mouth-x"},
            "suspension": setup()}
    if layout == "entries":
        entry = {key: value for key, value in data.items() if key != "schemaVersion"}
        entry["equipmentObjectID"] = "left"
        authoring = {"schemaVersion": 2, "entries": [entry, dict(entry, equipmentObjectID="right", suspension=setup())]}
    elif layout in ("instances", "entry-instances"):
        authoring = {key: value for key, value in data.items() if key != "suspension"}
        authoring.update(schemaVersion=2, instanceSuspensions={"left": setup(), "right": setup()})
        if layout == "entry-instances":
            authoring = {"schemaVersion": 2, "entries": [
                {key: value for key, value in authoring.items() if key != "schemaVersion"},
            ]}
    else:
        authoring = data
    media = {"type": "model", "descriptorPath": "assets/primary.model.json"}
    if layout != "single":
        media["instances"] = [{"equipmentObjectID": identifier} for identifier in ("left", "right")]
    board = {"presentations": [{"id": "view", "media": media}]}
    source = write_native_authoring(package, board, authoring)
    document = cad_source.materialize_suspension(
        authoring, {"view": digest}, hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    for entry in document.get("entries", [document]):
        for setup in entry.get("instanceSuspensions", {"": entry.get("suspension")}).values():
            for pose in setup["canonicalPoses"].values():
                if native:
                    pose["wrappedRoutes"] = {"strand": [[0, 0, 0], [0, .01, 0], [0, .02, 0]]}
                else:
                    pose["cordContactPoints"] = {
                        passage["id"]: [passage["pointInModel"]]
                        for passages in setup["passages"].values() for passage in passages
                    }
    authored_bytes = source.read_bytes()
    sidecar = package / "assets/suspension.json"
    sidecar.write_text(json.dumps(document))
    solid = tmp_path / "solid.json"
    solid.write_text(json.dumps({"sourcePackage": "fixture", "sourceFeature": "FinalSolid",
        "sourceSHA256": hashlib.sha256(source.read_bytes()).hexdigest(), "vertices": [], "triangles": []}))
    calls = []
    closed = []
    shape = SimpleNamespace(isValid=lambda: True, Solids=[object()])
    cad = SimpleNamespace(Name="owned-native", getObject=lambda name: SimpleNamespace(Shape=shape))
    monkeypatch.setitem(sys.modules, "FreeCAD", SimpleNamespace(openDocument=lambda path: cad, closeDocument=closed.append))
    def solve(mesh, local, model, **kwargs):
        assert (mesh.metadata.get("nativeSolid") is shape) == (not native)
        calls.append(local)
        generated = {"strand": [[0, 0, 0], [0, .5, 0], [0, 1, 0]]} if native else {
            passage["id"]: [[passage["pointInModel"][0], .1, passage["pointInModel"][2]]]
            for passages in local["suspension"]["passages"].values() for passage in passages
        }
        return {"pose": {"height": -.1, "routes" if native else "contacts": generated}}
    monkeypatch.setitem(sys.modules, "native_cord_routes", SimpleNamespace(solve_native_routes=solve))
    monkeypatch.setattr(solver, "solve_package", lambda package, mesh, local, model: solve(mesh, local, model))
    monkeypatch.setattr(solver, "ROOT", tmp_path)
    monkeypatch.setattr(solver.trimesh, "Trimesh", lambda **kwargs: SimpleNamespace(metadata={}))
    report = tmp_path / "report.json"
    argv = ["solve", "--package", "fixture", "--solid", str(solid), "--apply", "--report", str(report)]
    if layout in ("entries", "entry-instances"): argv += ["--presentation", "view"]
    if select: argv += ["--equipment-object", "left"]
    monkeypatch.setattr(sys, "argv", argv)
    if layout == "entries" and not select:
        with pytest.raises(ValueError, match="select exactly one"):
            solver.main()
        assert source.read_bytes() == authored_bytes
        assert json.loads(sidecar.read_text()) == document
        assert not report.exists()
        return
    solver.main()
    assert source.read_bytes() == authored_bytes
    assert cad_source.load_suspension_authoring(source) == authoring
    result = json.loads(sidecar.read_text())
    assert result["schemaVersion"] == document["schemaVersion"]
    assert len(calls) == (2 if layout in ("instances", "entry-instances") and not select else 1)
    assert closed == ([] if native else ["owned-native"])
    if layout == "entries":
        changed = result["entries"][0]["suspension"]
        assert result["entries"][1] == document["entries"][1]
    elif layout in ("instances", "entry-instances"):
        result_setups = (result["entries"][0] if layout == "entry-instances" else result)["instanceSuspensions"]
        previous_setups = (document["entries"][0] if layout == "entry-instances" else document)["instanceSuspensions"]
        changed = result_setups["left"]
        if select: assert result_setups["right"] == previous_setups["right"]
        else: assert result_setups["right"]["canonicalPoses"]["pose"]["translation"] == [0, -.1, 0]
    else: changed = result["suspension"]
    assert changed["canonicalPoses"]["pose"]["translation"] == [0, -.1, 0]
    assert ("wrappedRoutes" if native else "cordContactPoints") in changed["canonicalPoses"]["pose"]
    cad_source.merge_suspension_artifact(board, package, source)
    assert ("instances" if layout in ("instances", "entry-instances") else "poses") in json.loads(report.read_text())
