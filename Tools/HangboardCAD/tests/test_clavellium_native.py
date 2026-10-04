"""Verify owner-confirmed through-passages and the actual settled sling loop."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "Tools/HangboardCAD"
FREECAD = Path(os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"))
pytestmark = pytest.mark.skipif(not FREECAD.is_file(), reason="native FreeCAD unavailable")


def test_all_three_sling_channels_are_open_and_contacts_stay_valid(tmp_path):
    script = tmp_path / "check.py"
    script.write_text('''import FreeCAD as App
from pathlib import Path
d = App.openDocument(str(Path("Hangboards/clavellium-training-block.FCStd").resolve()))
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
    result = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD), str(script)],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "connected passages and contact inventory verified" in result.stdout


def test_all_pinch_contact_faces_point_outward(tmp_path):
    script = tmp_path / "pinch_normals.py"
    script.write_text('''import FreeCAD as App
from pathlib import Path
d = App.openDocument(str(Path("Hangboards/clavellium-training-block.FCStd").resolve()))
for name, expected in {
    "Pinch80Left": (-1, 0, 0), "Pinch80Right": (1, 0, 0),
    "Pinch90Front": (0, -1, 0), "Pinch90Back": (0, 1, 0),
    "Pinch100Top": (0, 0, 1), "Pinch100Bottom": (0, 0, -1),
}.items():
    points, triangles = d.getObject(name).Shape.tessellate(0.12)
    assert triangles, name
    outward = App.Vector(*expected)
    for a, b, c in triangles:
        normal = (points[b] - points[a]).cross(points[c] - points[a])
        assert normal.dot(outward) > 0, name + " is back-facing"
App.closeDocument(d.Name)
print("all six pinch contact faces point outward")
''')
    result = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD), str(script)],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all six pinch contact faces point outward" in result.stdout


def test_cached_single_loop_matches_the_native_solid_solve(tmp_path):
    pytest.importorskip("trimesh")
    pytest.importorskip("shapely")
    pytest.importorskip("rtree")
    import trimesh
    sys.path.insert(0, str(TOOLS))
    from solve_threaded_rope import solve_package

    solid_path = tmp_path / "clavellium-solid.json"
    env = dict(os.environ, HANGTEN_ROPE_PACKAGE="clavellium-training-block",
               HANGTEN_ROPE_SOLID_FEATURE="Pinch100BottomReliefCut",
               HANGTEN_ROPE_SOLID_OUTPUT=str(solid_path))
    result = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD),
                             str(TOOLS / "export_rope_collision_solid.py")],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    source = json.loads(solid_path.read_text())
    mesh = trimesh.Trimesh(vertices=source["vertices"], faces=source["triangles"], process=False)
    package = ROOT / "Hangboards/clavellium-training-block"
    sidecar = json.loads((package / "assets/suspension.json").read_text())
    assert sidecar["suspension"]["branches"][0]["radius"] == 0.0035, "owner-confirmed 7 mm diameter"
    descriptor = json.loads((package / "assets/primary.model.json").read_text())
    solved = solve_package("clavellium-training-block", mesh, sidecar, descriptor)["front"]
    pose = sidecar["suspension"]["canonicalPoses"]["front"]
    assert solved["contacts"] == pose["cordContactPoints"]
    assert solved["height"] == pose["translation"][1]
    assert solved["lengths"]["sling-loop"] == pytest.approx(0.55, rel=0, abs=1e-6)
    # The solver itself rejects any sampled native-solid collision. Also
    # require the two cached mouth ends to span the real 90 mm passage.
    assert pose["cordContactPoints"]["sling-front"][-1] == [0, 0.0025, 0.045]
    assert pose["cordContactPoints"]["sling-back"][0] == [0, 0.0025, -0.045]



def test_axis_tagged_rectangular_channels_use_the_declared_dimension(tmp_path):
    script = tmp_path / "box-axes.py"
    script.write_text('''import FreeCAD as App
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path("Tools/HangboardCAD").resolve()))
from measure_channel_spines import box_axis_samples,channel_samples,station_on_spine,model_to_native
# Non-cubic dimensions make a wrong axis mapping visible; also retain placement.
d=App.newDocument("RectangularChannelAxisRegression")
box=d.addObject("Part::Box","Channel")
box.Length=10;box.Width=20;box.Height=30
box.addProperty("App::PropertyString","HangTenChannelAxis")
box.Placement=App.Placement(App.Vector(4,5,6),App.Rotation(App.Vector(0,0,1),90))
for axis,length in [("x",10),("y",20),("z",30)]:
 box.HangTenChannelAxis=axis
 points=channel_samples(box,box.Name)
 assert abs(points[0].distanceToPoint(points[1])-length)<1e-9
 local=[box.Placement.inverse().multVec(p) for p in points]
 values=[list(p) for p in local]
 index="xyz".index(axis)
 assert abs(values[0][index])<1e-9 and abs(values[1][index]-length)<1e-9
App.closeDocument(d.Name)
p=Path("Hangboards/clavellium-training-block")
d=App.openDocument(str(p.with_suffix(".FCStd").resolve()))
for name in ["CenterChannelTool","LowerLeftChannelTool","LowerRightChannelTool"]:
 box=d.getObject(name)
 assert box.HangTenChannelAxis=="y" and float(box.Width)==92
 samples=box_axis_samples(box)
 assert abs(samples[0].distanceToPoint(samples[-1])-92)<1e-9
s=json.loads(d.HangTenSuspensionAuthoring)["suspension"]
passages=s["passages"]["left"]
samples=channel_samples(d.getObject("CenterChannelTool"),"CenterChannelTool")
stations=[station_on_spine(model_to_native(p["pointInModel"]),samples) for p in passages]
assert abs(abs(stations[1]-stations[0])/1000-s["internalLoop"]["channelLengthByBranchID"]["sling-loop"])<1e-9
App.closeDocument(d.Name)
print("axis dimensions and real Clavellium channel measurement verified")
''')
    run=subprocess.run([sys.executable,str(TOOLS/"run_freecad.py"),"--freecad",str(FREECAD),str(script)],
                       cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert run.returncode==0,run.stdout+run.stderr
    assert "axis dimensions and real Clavellium channel measurement verified" in run.stdout
