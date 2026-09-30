"""Owner-confirmed 7 mm cords must not retain the old undersized CAD bore."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
TOOLS=ROOT/"Tools/HangboardCAD"

def test_mini_bar_uses_the_confirmed_seven_mm_cord():
    document=json.loads((ROOT/"Hangboards/lattice-mini-bar/suspension.json").read_text())
    assert all(branch["radius"] == .0035 for branch in document["suspension"]["branches"])

def test_exported_contact_regions_leave_the_native_cord_mouths_open():
    pytest.importorskip("trimesh")
    import numpy as np
    import trimesh
    sys.path.insert(0,str(TOOLS))
    from usdz_writer import read_usdz
    nodes=read_usdz(ROOT/"Hangboards/lattice-mini-bar/assets/primary.usdz")["nodes"]
    vertices=[];faces=[]
    for node in nodes.values():
        faces.extend(np.asarray(node["triangles"])+len(vertices))
        vertices.extend(node["points_m"])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    mouths=[[-.069,.024,.1],[-.057,.024,.1],[.057,.024,.1],[.069,.024,.1]]
    hits,_,_=mesh.ray.intersects_location(mouths,[[0,0,-1]]*4)
    assert len(hits)>0
    assert all(point[2] < .03 for point in hits), "Contact overlays must not cap the actual bore openings"

@pytest.mark.skipif(not Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd").is_file(),reason="FreeCAD unavailable")
def test_curved_channel_section_recovers_a_connected_bearing_outline(tmp_path):
    pytest.importorskip("trimesh")
    pytest.importorskip("shapely")
    import numpy as np
    import trimesh
    from shapely.geometry import Polygon, Point
    sys.path.insert(0,str(TOOLS))
    from solve_threaded_rope import bearing_section
    solid=tmp_path/"mini-solid.json"
    environment=dict(os.environ,HANGTEN_ROPE_PACKAGE="lattice-mini-bar",
                     HANGTEN_ROPE_SOLID_FEATURE="RightCordChannel",
                     HANGTEN_ROPE_SOLID_OUTPUT=str(solid))
    run=subprocess.run([sys.executable,str(TOOLS/"run_freecad.py"),str(TOOLS/"export_rope_collision_solid.py")],cwd=ROOT,env=environment,capture_output=True,text=True,timeout=60)
    assert run.returncode == 0,run.stdout+run.stderr
    data=json.loads(solid.read_text())
    mesh=trimesh.Trimesh(vertices=data["vertices"],faces=data["triangles"],process=False)
    section=mesh.section(plane_origin=[-.069,0,0],plane_normal=[1,0,0])
    pieces=[Polygon(np.asarray(loop)[:,[1,2]]) for loop in section.discrete]
    outline=bearing_section(pieces,[.024,.067183],.0036)
    assert outline.is_valid and outline.geom_type == "Polygon" and not outline.interiors
    assert not outline.contains(Point(.024,.067183))

@pytest.mark.skipif(not Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd").is_file(),reason="FreeCAD unavailable")
def test_mini_bar_native_passages_fit_seven_mm_without_changing_board_scale(tmp_path):
    script=tmp_path/"confirmed-diameter.py"
    script.write_text('''import FreeCAD as App
from pathlib import Path
d=App.openDocument(str(Path("Hangboards/lattice-mini-bar/lattice-mini-bar.FCStd").resolve()))
for name in ["LeftChannelDiameter","RightChannelDiameter"]:
    sketch=d.getObject(name)
    assert sketch.Geometry[0].Radius >= 3.6, "Native display bore must admit the owner's 7 mm cord plus clearance"
    assert "display estimate" in sketch.DiameterProvenance.lower()
body=d.getObject("RightCordChannel").Shape
assert body.isValid() and len(body.Solids)==1
assert abs(body.BoundBox.XLength-155)<1e-7
App.closeDocument(d.Name)
''')
    run=subprocess.run([sys.executable,str(TOOLS/"run_freecad.py"),str(script)],cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert run.returncode == 0,run.stdout+run.stderr
