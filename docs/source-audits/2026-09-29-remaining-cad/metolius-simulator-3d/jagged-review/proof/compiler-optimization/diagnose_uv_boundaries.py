import sys,json,math
from pathlib import Path
import FreeCAD as A
h=Path(__file__).resolve().parent;root=Path.cwd();sys.path.insert(0,str(root/'Tools/HangboardCAD'));import compile_board as c
report=json.loads((root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author/final-normal-comparison.json').read_text());bad=[r for r in report['comparisons'] if r['angleDegrees']>.001]
d=A.openDocument(str(root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author/candidate/metolius-simulator-3d.FCStd'));shape=d.BodySolid.Shape;p,t=shape.tessellate(.28);ids=sorted(set(r['triangle'] for r in bad));cache=c._uv_node_normal_cache(shape,p,[t[i] for i in ids],.28);rows=[]
def angle(a,b):a=A.Vector(a);b=A.Vector(b);a.normalize();b.normalize();return math.degrees(math.acos(max(-1,min(1,abs(a.dot(b))))))
for badrow in bad:
 ti=badrow['triangle'];corner=badrow['corner'];tri=t[ti];q=p[tri[corner]];owner,ns=cache[ids.index(ti)];face=shape.Faces[owner];uvs=sorted(face.getUVNodes(),key=lambda uv:(face.Surface.value(*uv)-q).Length);uv=uvs[0];inverse=face.Surface.parameter(q)
 centroid=sum((p[i] for i in tri),A.Vector())/3;flat=(p[tri[1]]-p[tri[0]]).cross(p[tri[2]]-p[tri[0]]);flat.normalize();best=None;legacyowner=None
 for fi,f in enumerate(shape.Faces):
  box=f.BoundBox;box.enlarge(.56)
  if not box.isInside(centroid):continue
  u,v=f.Surface.parameter(centroid);distance=(f.Surface.value(u,v)-centroid).Length
  if distance>.420001 or not f.isPartOfDomain(u,v):continue
  normal=f.normalAt(u,v);key=(distance,-abs(normal.dot(flat)))
  if best is None or key<best:best=key;legacyowner=fi
 surf=face.Surface;knots={}
 for axis in ['U','V']:
  if hasattr(surf,'get'+axis+'Knots'):
   kk=getattr(surf,'get'+axis+'Knots')();mm=getattr(surf,'get'+axis+'Multiplicities')();value=uv[0 if axis=='U' else 1];i=min(range(len(kk)),key=lambda i:abs(kk[i]-value));knots[axis]={'value':value,'nearestKnot':kk[i],'distance':abs(kk[i]-value),'multiplicity':mm[i],'degree':getattr(surf,axis+'Degree')}
 rows.append({'triangle':ti,'corner':corner,'point':[q.x,q.y,q.z],'exactOwner':owner,'legacyOwner':legacyowner,'nativeUV':list(uv),'inverseUV':list(inverse),'uvMatchDistanceMM':(surf.value(*uv)-q).Length,'sameFaceUVVsInverseNormalAngle':angle(face.normalAt(*uv),face.normalAt(*inverse)),'faceParameterRange':face.ParameterRange,'nearestKnots':knots})
(h/'uv-boundary-diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2));A.closeDocument(d.Name)
