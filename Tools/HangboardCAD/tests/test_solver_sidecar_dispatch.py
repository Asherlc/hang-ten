"""Merge regressions for both retained sidecar shapes and solver backends."""
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


@pytest.mark.parametrize("layout,native,select", [
    ("single", True, False), ("entries", True, True),
    ("instances", True, False), ("instances", False, False),
    ("instances", False, True),
])
def test_sidecar_dispatch_preserves_document_and_updates_only_selected_setups(tmp_path, monkeypatch, layout, native, select):
    package = tmp_path / "Hangboards" / "fixture"
    (package / "assets").mkdir(parents=True)
    source = package / "fixture.FCStd"
    source.write_bytes(b"native fixture")
    digest = "a" * 64
    (package / "assets/primary.model.json").write_text(json.dumps({"modelSHA256": digest}))
    def setup():
        return {"type": "cadRoutedCord" if native else "threadedLoopCord",
                "canonicalPoses": {"pose": {"translation": [0, 0, 0]}}}
    data = {"schemaVersion": 1, "presentationID": "view", "modelSHA256": digest,
            "ropeSolver": {"method": "nativeRoutes"} if native else {"sectionPlane": "mouth-x"},
            "suspension": setup()}
    if layout == "entries":
        entry = {key: value for key, value in data.items() if key != "schemaVersion"}
        entry["equipmentObjectID"] = "left"
        document = {"schemaVersion": 2, "entries": [entry, dict(entry, equipmentObjectID="right", suspension=setup())]}
    elif layout == "instances":
        document = {key: value for key, value in data.items() if key != "suspension"}
        document.update(schemaVersion=2, instanceSuspensions={"left": setup(), "right": setup()})
    else:
        document = data
    sidecar = package / "suspension.json"
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
        return {"pose": {"height": -.1, "routes" if native else "contacts": {"strand": [[0, 0, 0], [0, 1, 0]]}}}
    monkeypatch.setitem(sys.modules, "native_cord_routes", SimpleNamespace(solve_native_routes=solve))
    monkeypatch.setattr(solver, "solve_package", lambda package, mesh, local, model: solve(mesh, local, model))
    monkeypatch.setattr(solver, "ROOT", tmp_path)
    monkeypatch.setattr(solver.trimesh, "Trimesh", lambda **kwargs: SimpleNamespace(metadata={}))
    monkeypatch.setattr(cad_source, "load_board", lambda path: {"presentations": [{"id": "view", "media": {"descriptorPath": "assets/primary.model.json"}}]})
    report = tmp_path / "report.json"
    argv = ["solve", "--package", "fixture", "--solid", str(solid), "--apply", "--report", str(report)]
    if layout == "entries": argv += ["--presentation", "view", "--equipment-object", "left"]
    elif select: argv += ["--equipment-object", "left"]
    monkeypatch.setattr(sys, "argv", argv)
    solver.main()
    result = json.loads(sidecar.read_text())
    assert result["schemaVersion"] == document["schemaVersion"]
    assert len(calls) == (2 if layout == "instances" and not select else 1)
    assert closed == ([] if native else ["owned-native"])
    if layout == "entries":
        changed = result["entries"][0]["suspension"]
        assert result["entries"][1] == document["entries"][1]
    elif layout == "instances":
        changed = result["instanceSuspensions"]["left"]
        if select: assert result["instanceSuspensions"]["right"] == document["instanceSuspensions"]["right"]
    else: changed = result["suspension"]
    assert changed["canonicalPoses"]["pose"]["translation"] == [0, -.1, 0]
    assert ("wrappedRoutes" if native else "cordContactPoints") in changed["canonicalPoses"]["pose"]
    assert ("instances" if layout == "instances" else "poses") in json.loads(report.read_text())
