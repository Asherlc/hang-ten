import sys,json,hashlib,math
from pathlib import Path
import FreeCAD as A
import Part
h=Path(__file__).resolve().parent;source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source)
d=A.openDocument(str(source));d.recompute();body=d.getObject('BodySolid').Shape
fail=[]
def check(k,v):
 if not v:fail.append(k)
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,a.dot(b)/(a.Length*b.Length)))))
def roof(shape,x,y,normal=False):
 line=Part.makeLine(A.Vector(x,y,100),A.Vector(x,y,240));cut=shape.common(line)
 if not cut.Vertexes:return None
 z=max(v.Point.z for v in cut.Vertexes);point=A.Vector(x,y,z);ns=[]
 if normal:
  for f in shape.Faces:
   b=f.BoundBox
   if x<b.XMin-1e-5 or x>b.XMax+1e-5 or y<b.YMin-1e-5 or y>b.YMax+1e-5 or z<b.ZMin-1e-5 or z>b.ZMax+1e-5:continue
   if f.distToShape(Part.Vertex(point))[0]<1e-5:
    u,v=f.Surface.parameter(point);n=f.normalAt(u,v)
    if n.z>0:ns.append(n)
 return {'zMM':z,'normals':[[n.x,n.y,n.z] for n in ns]}

rows=[]
for x in [63,65,130,132,164,166,238,240]:
 for y in [-54.9,-64.9]:
  probes=[]
  for eps in [.001,.0001]:
   left=roof(body,x-eps,y,True);right=roof(body,x+eps,y,True)
   angles=[angle(A.Vector(*a),A.Vector(*b)) for a in left['normals'] for b in right['normals']] if left and right else []
   probes.append({'epsilonMM':eps,'left':left,'right':right,'heightDifferenceMM':abs(left['zMM']-right['zMM']) if left and right else None,'maxNormalAngleDegrees':max(angles) if angles else None})
  rows.append({'xMM':x,'yMM':y,'probes':probes})
singular=[]
for x in [63,132]:
 probes=[]
 for eps in [.01,.001,.0001,.00001]:
  left=roof(body,x-eps,-65);right=roof(body,x+eps,-65)
  probes.append({'epsilonMM':eps,'left':left,'right':right,'heightDifferenceMM':abs(left['zMM']-right['zMM']) if left and right else None})
 singular.append({'xMM':x,'yMM':-65,'probes':probes})
r={'sourceSHA256':before,'interiorSections':rows,'grazingSections':singular,'sourceBytesUnchanged':sha(source)==before,'note':'Interior offset0.1mm avoids exact55/65mm support-depth boundary; finer grazing probes distinguish shrinking curved-edge differences from a finite roof step. Normals at intended support lips must not be interpreted as cross-strip seams.'}
out.write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);print(json.dumps(r,indent=2))
