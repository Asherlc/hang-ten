"""Verify owner-confirmed through-passages and the actual settled sling loop."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "Tools/HangboardCAD"
FREECAD = Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")
pytestmark = pytest.mark.skipif(not FREECAD.is_file(), reason="native FreeCAD unavailable")


def test_all_three_sling_channels_are_open_and_contacts_stay_valid(tmp_path):
    script = tmp_path / "check.py"
    script.write_text('''import FreeCAD as App
from pathlib import Path
d = App.openDocument(str(Path("Hangboards/clavellium-training-block/clavellium-training-block.FCStd").resolve()))
s = d.getObject("Pinch100BottomReliefCut").Shape
assert s.isValid() and len(s.Solids) == 1
for x, z in [(0, 2.5), (-24, -33.5), (24, -33.5)]:
    for y in range(-45, 46):
        assert not s.isInside(App.Vector(x, y, z), 1e-6, True), "blind channel"
for name in ["CenterChannelTool", "LowerLeftChannelTool", "LowerRightChannelTool"]:
    tool = d.getObject(name)
    assert tool.TypeId == "Part::Box" and tool.HangTenChannelAxis == "y"
    assert float(tool.Width) == 92
contacts = [o for o in d.Objects if getattr(o, "NodeRole", None) == "contact"]
assert len(contacts) == 10 and all(o.Shape.isValid() for o in contacts)
assert {o.ContactID for o in contacts} == {
    "cd-crimp-8mm", "cd-crimp-10mm", "cd-crimp-15mm", "cd-crimp-20mm",
    "cd-pinch-80mm-negative-x", "cd-pinch-80mm-positive-x",
    "cd-pinch-90mm-front", "cd-pinch-90mm-back",
    "cd-pinch-100mm-top", "cd-pinch-100mm-bottom"}
App.closeDocument(d.Name)
print("connected passages and contact inventory verified")
''')
    result = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), str(script)],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "connected passages and contact inventory verified" in result.stdout


def test_cached_single_loop_matches_the_native_solid_solve(tmp_path, monkeypatch):
    pytest.importorskip("trimesh")
    pytest.importorskip("shapely")
    import trimesh
    sys.path.insert(0, str(TOOLS))
    from solve_threaded_rope import solve_package

    solid_path = tmp_path / "clavellium-solid.json"
    env = dict(os.environ, HANGTEN_ROPE_PACKAGE="clavellium-training-block",
               HANGTEN_ROPE_SOLID_FEATURE="Pinch100BottomReliefCut",
               HANGTEN_ROPE_SOLID_OUTPUT=str(solid_path))
    result = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"),
                             str(TOOLS / "export_rope_collision_solid.py")],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    source = json.loads(solid_path.read_text())
    mesh = trimesh.Trimesh(vertices=source["vertices"], faces=source["triangles"], process=False)
    package = ROOT / "Hangboards/clavellium-training-block"
    sidecar = json.loads((package / "suspension.json").read_text())
    descriptor = json.loads((package / "assets/primary.model.json").read_text())
    solved = solve_package("clavellium-training-block", mesh, sidecar, descriptor)["front"]
    pose = sidecar["suspension"]["canonicalPoses"]["front"]
    assert solved["contacts"] == pose["cordContactPoints"]
    assert solved["height"] == pose["translation"][1]
    assert solved["lengths"]["sling-loop"] == pytest.approx(0.55, abs=1e-8)
    # The solver itself rejects any sampled native-solid collision. Also
    # require the two cached mouth ends to span the real 90 mm passage.
    assert pose["cordContactPoints"]["sling-front"][-1] == [0, 0.0025, 0.045]
    assert pose["cordContactPoints"]["sling-back"][0] == [0, 0.0025, -0.045]
