"""Physics geometry comes from the watertight CAD solid and editable channel."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "Tools/HangboardCAD"
FREECAD = Path(os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"))
pytestmark = pytest.mark.skipif(not FREECAD.is_file(), reason="FreeCAD unavailable")


def test_native_cylinder_bores_export_complete_circular_apertures(tmp_path):
    script=tmp_path/"cylinder-export.py"
    script.write_text('''import FreeCAD as App
import json,sys
from pathlib import Path
sys.path[:0]=[str(Path("Tools/HangboardCAD").resolve()),str(Path("Tools/HangboardPackages/src").resolve())]
from export_rope_physics import export_rope_physics
from hangboard_packages.rope_physics import _mesh,portal_clearance_radius
d=App.openDocument(str(Path("Hangboards/crimptonite-helium-mobile/crimptonite-helium-mobile.FCStd").resolve()))
mapping={"left":"LeftCordChannel","right":"RightCordChannel"}
a=export_rope_physics(d,"BodySolid",mapping)
b=export_rope_physics(d,"BodySolid",mapping)
assert json.dumps(a)==json.dumps(b)
assert len(a["channels"])==2 and len(a["portals"])==4
for channel in a["channels"]:
 _mesh({k:channel[k] for k in ["vertices","triangles"]})
 assert len(channel["spine"])==2
 for identifier in channel["portalIDs"]:
  p=next(p for p in a["portals"] if p["id"]==identifier)
  assert len(p["boundary"])>=64
  assert abs(abs(p["center"][0])-.186)<1e-9
  assert abs(p["center"][1])<1e-9
  assert abs(abs(p["center"][2])-.012)<1e-9
  assert abs(abs(p["normal"][2])-1)<1e-9
  assert .00349 < portal_clearance_radius(p) <= .0035
App.closeDocument(d.Name)
''')
    run=subprocess.run([sys.executable,str(TOOLS/"run_freecad.py"), "--freecad", str(FREECAD),str(script)],cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert run.returncode == 0,run.stdout+run.stderr


def test_curved_pipe_exports_native_void_and_safe_planar_crossings(tmp_path):
    script=tmp_path/"curved-export.py"
    script.write_text('''import FreeCAD as App
import json,sys
from pathlib import Path
sys.path[:0]=[str(Path("Tools/HangboardCAD").resolve()),str(Path("Tools/HangboardPackages/src").resolve())]
from export_rope_physics import export_rope_physics
from hangboard_packages.rope_physics import _mesh,portal_clearance_radius
d=App.openDocument(str(Path("Hangboards/lattice-mini-bar/lattice-mini-bar.FCStd").resolve()))
mapping={"left-loop":"LeftCordChannel","right-loop":"RightCordChannel"}
a=export_rope_physics(d,"RightCordChannel",mapping)
b=export_rope_physics(d,"RightCordChannel",mapping)
assert json.dumps(a)==json.dumps(b)
assert len(a["channels"])==2 and len(a["portals"])==4
for channel in a["channels"]:
 assert len(channel["spine"])>3
 _mesh({k:channel[k] for k in ["vertices","triangles"]})
 portals=[next(p for p in a["portals"] if p["id"]==i) for i in channel["portalIDs"]]
 assert channel["spine"][0]==portals[0]["center"]
 assert channel["spine"][-1]==portals[-1]["center"]
 assert all(portal_clearance_radius(p)>.0036 for p in portals)
 # Safe topological sections lie inside the curved CAD mouths; exact wood
 # collision, rather than a fictitious planar mouth, controls entry contact.
 assert all(.060 < p["center"][2] < .067183 for p in portals)
App.closeDocument(d.Name)
''')
    run=subprocess.run([sys.executable,str(TOOLS/"run_freecad.py"), "--freecad", str(FREECAD),str(script)],cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert run.returncode == 0,run.stdout+run.stderr


def test_clavellium_collision_and_portals_are_native_and_repeatable(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("trimesh")
    pytest.importorskip("rtree")
    output = tmp_path / "physics-geometry.json"
    script = tmp_path / "export.py"
    script.write_text(f'''import FreeCAD as App
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path("Tools/HangboardCAD").resolve()))
from export_rope_physics import export_rope_physics
d = App.openDocument(str(Path("Hangboards/clavellium-training-block/clavellium-training-block.FCStd").resolve()))
first = export_rope_physics(d, "Pinch100BottomReliefCut", {{"central": "CenterChannelTool"}})
second = export_rope_physics(d, "Pinch100BottomReliefCut", {{"central": "CenterChannelTool"}})
assert json.dumps(first) == json.dumps(second)
assert [p["center"] for p in first["portals"]] == [[0.0,0.0025,0.045],[0.0,0.0025,-0.045]]
assert first["channels"][0]["spine"] == [[0.0,0.0025,0.045],[0.0,0.0025,-0.045]]
for p in first["portals"]:
    assert max(v[1] for v in p["boundary"]) == 0.0155
    assert min(v[1] for v in p["boundary"]) == -0.0105
    assert max(v[0] for v in p["boundary"]) == 0.012
    assert min(v[0] for v in p["boundary"]) == -0.012
assert "cordContactPoints" not in json.dumps(first)
Path({str(output)!r}).write_text(json.dumps(first))
import Part
shape = d.getObject("Pinch100BottomReliefCut").Shape
samples = []
for x in [-9, 0, 9]:
    for z in [-8, 2.5, 12, 20]:
        for y in [-30, 0, 30]:
            p = App.Vector(x, y, z)
            samples.append({{"point":[x/1000,z/1000,-y/1000],
                            "inside":shape.isInside(p, 1e-7, True),
                            "distance":shape.distToShape(Part.Vertex(p))[0]/1000}})
Path({str(output.with_suffix('.samples.json'))!r}).write_text(json.dumps(samples))
App.closeDocument(d.Name)
''')
    run = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD), str(script)],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    import trimesh
    data = json.loads(output.read_text())
    for geometry in [data["collision"], *data["channels"]]:
        mesh = trimesh.Trimesh(vertices=geometry["vertices"], faces=geometry["triangles"], process=False)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
    wood = trimesh.Trimesh(vertices=data["collision"]["vertices"], faces=data["collision"]["triangles"], process=False)
    # Native model void: central passage is empty and its upper rail remains wood.
    assert not wood.contains([[0, .0025, 0]])[0]
    assert wood.contains([[0, .02, 0]])[0]
    import numpy as np
    samples = json.loads(output.with_suffix('.samples.json').read_text())
    points = np.asarray([sample['point'] for sample in samples])
    assert wood.contains(points).tolist() == [sample['inside'] for sample in samples]
    distances = trimesh.proximity.closest_point(wood, points)[1]
    # Flat channel boundaries have no tessellation approximation error.
    np.testing.assert_allclose(distances, [sample['distance'] for sample in samples], atol=1e-8)


def test_export_rejects_missing_body_and_channel_axis(tmp_path):
    script = tmp_path / "reject.py"
    script.write_text('''import FreeCAD as App
import sys
from pathlib import Path
sys.path.insert(0, str(Path("Tools/HangboardCAD").resolve()))
from export_rope_physics import export_rope_physics
d = App.openDocument(str(Path("Hangboards/clavellium-training-block/clavellium-training-block.FCStd").resolve()))
for body, channels in [("Missing", {}), ("Pinch100BottomReliefCut", {"central":"Missing"})]:
    try: export_rope_physics(d, body, channels)
    except ValueError: pass
    else: raise AssertionError("must reject missing source feature")
d.getObject("CenterChannelTool").HangTenChannelAxis = ""
try: export_rope_physics(d, "Pinch100BottomReliefCut", {"central":"CenterChannelTool"})
except ValueError: pass
else: raise AssertionError("must require operator-selected axis")
App.closeDocument(d.Name)
''')
    run = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD), str(script)],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr


def test_generated_descriptor_is_hash_bound_and_validated(tmp_path):
    import importlib.util
    sys.path.insert(0, str(ROOT / "Tools/HangboardPackages/src"))
    spec = importlib.util.spec_from_file_location("rope_fixture", ROOT / "Tools/HangboardPackages/tests/test_rope_physics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Only authoring profiles enter config; fixture collision/portals/channels
    # are replaced entirely by the native CAD export.
    profile_json = json.dumps(module.physics_fixture()["profiles"][0])
    script = tmp_path / "descriptor.py"
    script.write_text('''import FreeCAD as App
import sys, json, hashlib
from pathlib import Path
sys.path[:0] = [str(Path("Tools/HangboardCAD").resolve()),
               str(Path("Tools/HangboardPackages/src").resolve()),
               str(Path("Tools/HangboardPackages/tests").resolve())]
from export_rope_physics import build_physics_descriptor
source = Path("Hangboards/clavellium-training-block/clavellium-training-block.FCStd").resolve()
d = App.openDocument(str(source))
profile = json.loads(PROFILE_JSON)
profile["ropes"][0]["nodes"][1]["portalID"] = "central-front"
profile["ropes"][0]["nodes"][2]["portalID"] = "central-back"
config = {"bodyFeature":"Pinch100BottomReliefCut", "channelFeatures":{"central":"CenterChannelTool"}, "profiles":[profile]}
first = build_physics_descriptor(d, source, "a"*64, config)
assert json.dumps(first) == json.dumps(build_physics_descriptor(d, source, "a"*64, config))
assert first["modelSHA256"] == "a"*64
assert first["sourceSHA256"] == hashlib.sha256(source.read_bytes()).hexdigest()
channel = first["channels"][0]
assert channel["id"] == "central"
assert channel["portalIDs"] == ["central-front", "central-back"]
rope = first["profiles"][0]["ropes"][0]
assert [node["portalID"] for node in rope["nodes"] if node["kind"] == "portal"] == channel["portalIDs"]
from hangboard_packages.rope_physics import validate_rope_physics
assert validate_rope_physics(first, "a"*64) == first
config["profiles"][0]["ropes"][0].update(radius=.020, thicknessScale=10)
try: build_physics_descriptor(d, source, "a"*64, config)
except ValueError as error:
    assert "rope does not fit portal central-front" in str(error), str(error)
else: raise AssertionError("invalid enlarged rope must be rejected")
App.closeDocument(d.Name)
'''.replace('PROFILE_JSON', repr(profile_json)))
    run = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD), str(script)],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr


def test_compiler_removes_stale_physics_when_authoring_is_removed(tmp_path):
    import os
    import shutil
    pxr = pytest.importorskip("pxr")
    env = dict(os.environ, HANGTEN_CAD_PYTHONPATH=str(Path(pxr.__file__).parent.parent))
    source = tmp_path / "clavellium-training-block.FCStd"
    shutil.copyfile(ROOT / "Hangboards/clavellium-training-block/clavellium-training-block.FCStd", source)
    assets = tmp_path / "assets"
    assets.mkdir()
    authoring = tmp_path / "rope-physics.json"
    shutil.copyfile(ROOT / "Hangboards/clavellium-training-block/rope-physics.json", authoring)
    command = [sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD), str(TOOLS / "compile_board.py"),
               "--package", "clavellium-training-block", "--source", str(source), "--assets", str(assets)]
    first = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert first.returncode == 0, first.stdout + first.stderr
    physics_path = assets / "primary.physics.json"
    assert physics_path.is_file(), "Valid authoring must publish live physics"
    physics = json.loads(physics_path.read_text())
    model = json.loads((assets / "primary.model.json").read_text())
    assert physics["modelSHA256"] == model["modelSHA256"]
    authoring.unlink()
    second = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert second.returncode == 0, second.stdout + second.stderr
    assert (assets / "primary.usdz").is_file()
    assert not physics_path.exists()


def test_compiler_reports_malformed_physics_authoring_as_build_error(tmp_path):
    import os
    import shutil
    pxr = pytest.importorskip("pxr")
    env = dict(os.environ, HANGTEN_CAD_PYTHONPATH=str(Path(pxr.__file__).parent.parent))
    source = tmp_path / "clavellium-training-block.FCStd"
    shutil.copyfile(ROOT / "Hangboards/clavellium-training-block/clavellium-training-block.FCStd", source)
    (tmp_path / "rope-physics.json").write_text("[]")
    run = subprocess.run([sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD), str(TOOLS / "compile_board.py"),
                          "--package", "clavellium-training-block", "--source", str(source), "--check"],
                         cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode != 0
    assert "BUILD FAILED: invalid rope physics authoring" in run.stdout + run.stderr
    assert "Traceback" not in run.stdout + run.stderr
