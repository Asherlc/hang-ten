"""Check actual unbound exported surfaces against the native fitted insert."""
from pathlib import Path
import hashlib
import json
import os
import sys
import FreeCAD as App
import Part

ROOT=Path.cwd(); LANE=Path(__file__).resolve().parent
sys.path[:0]=[p for p in os.environ.get('HANGTEN_CAD_PYTHONPATH','').split(os.pathsep) if p]
sys.path.insert(0,str(ROOT/'Tools/HangboardCAD'))
from usdz_writer import read_usdz

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=LANE/'native-author/nature-stone-hanger.FCStd'
doc=App.openDocument(str(source))
try:
    doc.recompute()
    model=read_usdz(LANE/'assets/primary.usdz')
    assert not model['materials']
    assert all(n['material'] is None for n in model['nodes'].values())
    assert len(model['nodes'])==9 and len(model['members'])==1
    region=doc.getObject('Region_edge_front_20mm_granite').Shape
    granite_id='edge_front_20mm_granite_mesh_001'
    granite=model['nodes'][granite_id]
    def native(point):
        return App.Vector(point[0]*1000,-point[2]*1000,point[1]*1000)
    distances=[region.distToShape(Part.Vertex(native(p)))[0] for p in granite['points_m']]
    # The USD vertex storage is float32. This is the established 20 nm native
    # vertex correspondence budget, not tessellation deflection or a seam gap.
    assert max(distances)<.00002, 'Exported granite vertex is off its native region'
    bb=region.BoundBox
    overlap=0.; checked=0; triangles=set(); duplicates=0
    for node_id,node in model['nodes'].items():
        pts=[native(p) for p in node['points_m']]
        for indices in node['triangles']:
            p=[pts[i] for i in indices]
            key=tuple(sorted(tuple(round(v[j],6) for j in range(3)) for v in p))
            if key in triangles:duplicates+=1
            triangles.add(key)
            if node_id==granite_id:continue
            if max(v.x for v in p)<bb.XMin-.00002 or min(v.x for v in p)>bb.XMax+.00002:continue
            if max(v.z for v in p)<bb.ZMin-.00002 or min(v.z for v in p)>bb.ZMax+.00002:continue
            axis=None
            if all(abs(v.y+17.5)<.00002 for v in p):axis=1;value=-17.5
            elif all(abs(v.z+26)<.00002 for v in p):axis=2;value=-26.
            if axis is None:continue
            # Snap only the known planar depth coordinate for the Boolean
            # comparison, undoing USD float32 noise without changing x/z bounds.
            projected=[App.Vector(v.x,value,v.z) if axis==1 else App.Vector(v.x,v.y,value) for v in p]
            wire=Part.makePolygon(projected+[projected[0]])
            face=Part.Face(wire)
            if face.Area<1e-9:continue
            checked+=1
            overlap+=face.common(region).Area
    assert overlap<1e-5, 'Non-granite exported surface overlays exposed planar stone'
    assert duplicates==0, 'Export has duplicate triangles'
    report={'status':'pass','sourceSHA256':sha(source),
            'modelSHA256':sha(LANE/'assets/primary.usdz'),
            'descriptorSHA256':sha(LANE/'assets/primary.model.json'),
            'materials':0,'boundMeshMaterials':0,'archiveMembers':model['members'],
            'semanticNodes':len(model['nodes']),
            'triangles':sum(len(n['triangles']) for n in model['nodes'].values()),
            'graniteNativeVertexMaximumErrorMM':max(distances),
            'graniteVerticesChecked':len(distances),'foreignPlanarTrianglesChecked':checked,
            'foreignSurfaceOverStoneMM2':overlap,'duplicateTriangles':duplicates,
            'planeComparison':'Exact known native front/top planes; only float32 depth noise snapped within 0.00002 mm.'}
    (LANE/'independent-export-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
finally:
    App.closeDocument(doc.Name)
