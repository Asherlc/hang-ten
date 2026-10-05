"""Check actual planar USD mesh ownership without comparing chords to CAD arcs."""
from pathlib import Path
import hashlib
import json
import sys
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT=Path.cwd(); LANE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools/HangboardCAD'))
from usdz_writer import read_usdz
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
model=read_usdz(LANE/'assets/primary.usdz')
gid='edge_front_20mm_granite_mesh_001'
assert not model['materials'] and len(model['members'])==1
assert all(n['material'] is None for n in model['nodes'].values())
assert len(model['nodes'])==9
planes={key:{'granite':[],'other':[]} for key in ['front','top']}
duplicates=0; seen=set()
for name,node in model['nodes'].items():
    native=[(p[0]*1000,-p[2]*1000,p[1]*1000) for p in node['points_m']]
    for face in node['triangles']:
        pts=[native[i] for i in face]
        key=tuple(sorted(tuple(round(v,6) for v in p) for p in pts))
        if key in seen:duplicates+=1
        seen.add(key)
        kind='granite' if name==gid else 'other'
        if all(abs(p[1]+17.5)<.00002 for p in pts):
            poly=Polygon([(p[0],p[2]) for p in pts])
            if poly.area>1e-10:planes['front'][kind].append(poly)
        if all(abs(p[2]+26)<.00002 for p in pts):
            poly=Polygon([(p[0],p[1]) for p in pts])
            if poly.area>1e-10:planes['top'][kind].append(poly)
metrics={}
for plane,groups in planes.items():
    granite=unary_union(groups['granite'])
    other=unary_union(groups['other'])
    assert granite.is_valid and other.is_valid and granite.area>0
    overlap=granite.intersection(other).area
    metrics[plane]={'graniteTriangles':len(groups['granite']),
                    'otherPlanarTriangles':len(groups['other']),
                    'graniteAreaMM2':granite.area,'actualMeshOverlapMM2':overlap}
    assert overlap<1e-5, 'Exported wood/other mesh overlays the granite mesh'
assert duplicates==0
diagnostic=json.loads((LANE/'export-overlap-diagnostic.json').read_text())
report={'status':'pass','sourceSHA256':sha(LANE/'native-author/nature-stone-hanger.FCStd'),
        'modelSHA256':sha(LANE/'assets/primary.usdz'),
        'descriptorSHA256':sha(LANE/'assets/primary.model.json'),
        'semanticNodes':9,'triangles':sum(len(n['triangles']) for n in model['nodes'].values()),
        'materials':0,'boundMeshMaterials':0,'archiveMembers':model['members'],
        'duplicateTriangles':duplicates,'planarBoundaryChecks':metrics,
        'graniteVerticesOnNativeRegionMaximumErrorMM':diagnostic['maximumGraniteVertexErrorMM'],
        'priorAnalyticBoundaryDiagnostic':{
            'areaMM2':diagnostic['totalOverlapMM2'],
            'explanation':'Analytic rounded CAD corners compared against polygonal mesh chords produced expected arc/chord slivers. This is not overlap between the exported material surfaces. The actual exported triangle footprints are checked directly above.'}}
(LANE/'independent-export-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
