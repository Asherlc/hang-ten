"""Reopen, edit, save and reopen the native Original Grindstone source.

Run with run_freecad.py; scratch output stays below the current workspace.
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Hangboards/tension-grindstone-original.FCStd'


def check_document(doc, edited=False):
    doc.recompute()
    for obj in doc.Objects:
        assert not set(obj.State) & {'Invalid', 'Error', 'Touched', 'Recompute'}, (obj.Name, obj.State)
        assert obj.TypeId not in {'Part::Feature', 'PartDesign::Feature', 'Mesh::Feature'}, obj.Name
        if obj.TypeId == 'Sketcher::SketchObject':
            assert obj.FullyConstrained, obj.Name
    solid = doc.getObject('CavityLipChamfers').Shape
    boundary = Part.makeShell(solid.Faces)
    assert solid.isValid() and len(solid.Solids) == 1
    manifest = json.loads(doc.HangTenBoardManifest)
    nodes = [o for o in doc.Objects if getattr(o, 'NodeRole', '') == 'contact']
    assert len(nodes) == 12
    assert {o.ContactID for o in nodes} == {c['id'] for c in manifest['contacts']}
    for obj in nodes:
        expected = obj.HangTenGripDepthMm
        if edited and obj.ContactID == 'edge-15-left':
            expected = 17
        assert abs(obj.Shape.BoundBox.YLength - expected) < 0.01, (obj.ContactID, obj.Shape.BoundBox)
        # Distance to boundary faces, not distance to the interior of a solid.
        for vertex in obj.Shape.Vertexes:
            assert boundary.distToShape(Part.Vertex(vertex.Point))[0] < 0.01, obj.ContactID
    # Fifty-millimetre centre cavity is genuinely through; the other cavities
    # retain their native floors. No front cap can hide these openings.
    for y in (-49, -25, -1):
        assert not solid.isInside(App.Vector(0, y, 92), 1e-6, True)
    for x, z, front, depth in [(-128, 164, -60, 35), (128, 164, -60, 35),
                             (-256, 92, -50, 30), (-128, 92, -50, 25),
                             (128, 92, -50, 30), (256, 92, -50, 25),
                             (-256, 29, -32, 20), (-128, 29, -32, 17 if edited else 15),
                             (0, 29, -32, 22), (128, 29, -32, 20), (256, 29, -32, 15)]:
        assert not solid.isInside(App.Vector(x, front + depth - 0.5, z), 1e-6, True)
        assert solid.isInside(App.Vector(x, front + depth + 0.5, z), 1e-6, True)
    assert not solid.isInside(App.Vector(0, -13, 185), 1e-6, True)
    assert solid.isInside(App.Vector(0, -13, 177), 1e-6, True)
    assert not any('phone' in o.ContactID.lower() for o in nodes)
    return solid.Volume


def main(work):
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    doc = App.openDocument(str(SOURCE))
    original_volume = check_document(doc)
    pocket = doc.getObject('Edge15LeftPocket')
    pocket.Length = 17
    edited_volume = check_document(doc, edited=True)
    assert edited_volume < original_volume - 1000
    edited = work / 'persisted-depth-edit.FCStd'
    doc.saveAs(str(edited))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(edited))
    assert abs(doc.getObject('Edge15LeftPocket').Length.Value - 17) < 1e-8
    assert abs(check_document(doc, edited=True) - edited_volume) < 0.01
    App.closeDocument(doc.Name)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == digest
    print('all original Grindstone native source checks passed', flush=True)
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1:
        raise SystemExit(main(Path(sys.argv[1])))
    (ROOT / '.context').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=ROOT.name + '-grindstone-native-', dir=ROOT / '.context') as scratch:
        raise SystemExit(main(Path(scratch)))
