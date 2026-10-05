import json, hashlib, sys
from pathlib import Path
import FreeCAD as App
import Part

here = Path(__file__).resolve().parent
source = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
baseline = json.loads((here/'baseline.json').read_text())
before = hashlib.sha256(source.read_bytes()).hexdigest()
document = App.openDocument(str(source))
document.recompute()
body = document.getObject('BodySolid').Shape
shell = Part.makeCompound(body.Shells)
contacts = {o.ContactID: o for o in document.Objects if getattr(o, 'NodeRole', '') == 'contact'}
expected_ids = {c['id'] for c in baseline['contacts']}
failures = []
def check(label, value):
    if not value: failures.append(label)
def state(obj):
    b = obj.Shape.optimalBoundingBox()
    return [obj.Shape.Area, b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]
def clean(doc):
    return [(o.Name, list(o.State)) for o in doc.Objects if set(o.State) & {'Invalid', 'Error', 'Touched', 'Recompute'}]

check('recompute clean', not clean(document))
check('one valid final solid', body.isValid() and len(body.Solids) == 1)
check('exact embedded manifest', document.HangTenBoardManifest == (here/'before-manifest-raw.txt').read_text())
check('30 contact inventory', set(contacts) == expected_ids and len(contacts) == 30)
box = body.optimalBoundingBox()
envelope = [box.XLength, box.YLength, box.ZLength]
check('711x94x222 mm envelope (94 display estimate)', all(abs(a-b) < .02 for a,b in zip(envelope,[711,94,222])))
sketches = [o for o in document.Objects if o.TypeId == 'Sketcher::SketchObject']
check('fully constrained sketches', all(o.FullyConstrained for o in sketches))
depths = {}
for cid, expected in baseline['publishedDepthsMm'].items():
    measured = contacts[cid].Shape.optimalBoundingBox().YLength
    depths[cid] = {'expected': expected, 'actual': measured}
    check(cid+' published depth', abs(expected-measured) < .02)
surface_checks = {}
for cid, obj in contacts.items():
    check(cid+' valid surface', obj.Shape.isValid() and bool(obj.Shape.Faces) and not obj.Shape.Solids)
    distances = []
    for face in obj.Shape.Faces:
        u0,u1,v0,v1 = face.ParameterRange
        point = face.valueAt((u0+u1)/2,(v0+v1)/2)
        point = face.distToShape(Part.Vertex(point))[1][0][0]
        distances.append(shell.distToShape(Part.Vertex(point))[0])
        for vertex in face.Vertexes:
            distances.append(shell.distToShape(vertex)[0])
    surface_checks[cid] = {'faceCount':len(obj.Shape.Faces),'maxSampledShellDistanceMM':max(distances)}
    check(cid+' on final shell', max(distances) < .002)
    check(cid+' no rear proxy', not any(abs(f.BoundBox.YMin)<1e-6 and abs(f.BoundBox.YMax)<1e-6 for f in obj.Shape.Faces))
overlaps = []
items = list(contacts.items())
for i,(cid,obj) in enumerate(items):
    a = obj.Shape.BoundBox
    for other,target in items[i+1:]:
        b = target.Shape.BoundBox
        if a.XMin>b.XMax-1e-5 or a.XMax<b.XMin+1e-5 or a.YMin>b.YMax-1e-5 or a.YMax<b.YMin+1e-5 or a.ZMin>b.ZMax-1e-5 or a.ZMax<b.ZMin+1e-5:continue
        area = obj.Shape.common(target.Shape).Area
        if area > .001:overlaps.append({'first':cid,'second':other,'areaMM2':area})
check('no contact area overlap', not overlaps)
print('Native envelope, depths, contact shell and overlaps checked', flush=True)

initial={cid:state(obj) for cid,obj in contacts.items()}
params=document.getObject('Parameters');old_depth=params.Depth_edge_11_left;old_volume=body.Volume
params.Depth_edge_11_left=old_depth+2;document.recompute()
check('cavity edit recompute clean',not clean(document))
changed=[cid for cid,obj in contacts.items() if max(abs(a-b) for a,b in zip(initial[cid],state(obj)))>.001]
check('cavity edit only intended contact',changed==['edge-11-left'])
check('cavity edit reaches final solid',abs(document.getObject('BodySolid').Shape.Volume-old_volume)>.001)
check('cavity edit physical depth',abs(contacts['edge-11-left'].Shape.optimalBoundingBox().YLength-old_depth-2)<.02)
params.Depth_edge_11_left=old_depth;document.recompute()
check('cavity restore clean',not clean(document))
check('cavity restore all30regions',all(max(abs(a-b) for a,b in zip(initial[cid],state(obj)))<.001 for cid,obj in contacts.items()))
check('cavity restore final solid volume',abs(document.getObject('BodySolid').Shape.Volume-old_volume)<.001)
check('saved source unchanged',hashlib.sha256(source.read_bytes()).hexdigest()==before)
report={'status':'pass' if not failures else 'fail','blockingFindings':failures,'sourceSHA256':before,'envelopeXYZMM':envelope,
        'publishedDepthChecks':depths,'sampledFinalShellChecks':surface_checks,'contactOverlaps':overlaps,
        'nativeCavityEdit':{'parameter':'Depth_edge_11_left','before':old_depth,'after':old_depth+2,'changedContacts':changed},
        'sourceBytesUnchanged':True,'limits':'Final-shell membership samples each face and vertices; pairwise overlap is checked by native common surface area. Boundary/roof continuity and exported geometry are verified separately.'}
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'failures':failures,'report':str(out)},indent=2),flush=True)
App.closeDocument(document.Name)
raise SystemExit(bool(failures))
