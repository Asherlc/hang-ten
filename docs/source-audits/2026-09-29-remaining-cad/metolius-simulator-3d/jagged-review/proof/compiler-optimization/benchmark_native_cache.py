import sys,json,hashlib,time,math
from pathlib import Path
import FreeCAD as App
import Part
root=Path.cwd();here=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'Tools/HangboardCAD'));import compile_board as c
legacy={'__file__':str(root/'Tools/HangboardCAD/compile_board.py'),'__name__':'legacy_compile_board'}
exec(compile((here/'legacy_compile_board.py').read_text(),legacy['__file__'],'exec'),legacy)
source=root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author/candidate/metolius-simulator-3d.FCStd';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source)
# Default-path equivalence against the saved pre-change implementation.
fixture=Part.makeCylinder(20,10);p,t=fixture.tessellate(.28)
def plain(r):return ([[v.x,v.y,v.z] for v in r[0]],r[1],[[v.x,v.y,v.z] for v in r[2]])
old=plain(legacy['_surface_normals'](fixture,p,t,.28));new=plain(c._surface_normals(fixture,p,t,.28));assert old==new
start=time.monotonic();d=App.openDocument(str(source));shape=d.BodySolid.Shape;p,t=shape.tessellate(.28);cached=c._uv_node_normal_cache(shape,p,t,.28);cachetime=time.monotonic()-start
chosen=list(cached)[::max(1,len(cached)//20)][:20];sample=[t[i] for i in chosen]
start=time.monotonic();old=c._surface_normals(shape,p,sample,.28);legacytime=time.monotonic()-start
# Compare cached owner+normal per corner directly, independent of optimized loop.
angles=[]
for i in chosen:
 tri=t[i];flat=(p[tri[1]]-p[tri[0]]).cross(p[tri[2]]-p[tri[0]]);flat.normalize();actual=c._surface_normals(shape,p,[tri],.28)
 for n,reference in zip(cached[i][1],actual[2]):
  n=App.Vector(n);n.normalize()
  if n.dot(flat)<0:n=-n
  angles.append(math.degrees(math.acos(max(-1,min(1,n.dot(reference))))))
assert max(angles)<1e-4
r={'sourceSHA256':before,'compilerSHA256':sha(root/'Tools/HangboardCAD/compile_board.py'),'triangles':len(t),'points':len(p),'fastPathTriangles':len(cached),'fallbackTriangles':len(t)-len(cached),'openTessellateAndIndexSeconds':cachetime,'legacy20TriangleSeconds':legacytime,'comparedCorners':len(angles),'maximumNormalAngleDegrees':max(angles),'defaultCylinderOutputExactlyMatchesPreChange':old is not None and plain(c._surface_normals(fixture,*fixture.tessellate(.28),.28))==new,'sourceBytesUnchanged':sha(source)==before,'limits':'Bounded native cache construction and60corner comparison, not a whole-catalog or full optimized export validation.'}
(here/'native-cache-benchmark.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));App.closeDocument(d.Name)
