import sys,time,json,hashlib
from pathlib import Path
import numpy as np,trimesh
root=Path.cwd();sys.path.insert(0,str(root/'Tools/HangboardCAD'))
from native_cord_routes import NativeSection,checked_clearance,length
base=Path(__file__).resolve().parent; solid=json.loads((base.parent/'anchor-only/solid-primary.json').read_text())
mesh=trimesh.Trimesh(vertices=solid['vertices'],faces=solid['triangles'],process=False)
start=np.array([0,.292933085,0]);finish=np.array([-.05,0,.024]);result={}
for name in ('aStar','dijkstra'):
 section=NativeSection.for_span(mesh,start,finish,[1,0,0],.0015,.0002,path_search=name)
 begin=time.monotonic();path=section.route(start,finish);elapsed=time.monotonic()-begin
 row={'seconds':elapsed,'expandedBoundaryVertices':len(section.adj),'totalBoundaryVertices':len(section.points),'length':length(path),'path':path.tolist(),'certifiedClearance':checked_clearance(mesh,path,.0015)}
 result[name]=row;print(name,json.dumps({k:v for k,v in row.items() if k!='path'}),flush=True)
assert abs(result['aStar']['length']-result['dijkstra']['length'])<1e-10
result['exactSamePath']=result['aStar']['path']==result['dijkstra']['path']
result['sourceSHA256']=solid['sourceSHA256'];result['solverSHA256']=hashlib.sha256((root/'Tools/HangboardCAD/native_cord_routes.py').read_bytes()).hexdigest()
(base/'production-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
