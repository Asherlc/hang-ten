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
outline={}
for name in ['Silhouette0','Silhouette1','Silhouette2']:
 sk=d.getObject(name);rows=[]
 for i,g in enumerate(sk.Geometry):
  n=sk.Geometry[(i+1)%len(sk.Geometry)];gap=(g.EndPoint-n.StartPoint).Length;ang=angle(g.tangent(g.LastParameter)[0],n.tangent(n.FirstParameter)[0]);rows.append({'join':i,'point':[g.EndPoint.x,g.EndPoint.y],'gapMM':gap,'tangentAngleDegrees':ang});check(name+str(i)+' closed G1 join',gap<1e-5 and ang<.001)
 outline[name]=rows
print('Outline joins measured',flush=True)

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

stations=[35,37,47,63,65,130,132,148,164,166,238,240,258,276,278];rows=[];mirror=[]
for x in stations:
 for y in [-10,-40,-55,-65]:
  probes=[]
  for eps in [.01,.001]:
   left=roof(body,x-eps,y,True);right=roof(body,x+eps,y,True)
   check(f'x{x}/y{y} roof exists',left is not None and right is not None)
   if left is None or right is None:continue
   diff=right['zMM']-left['zMM'];angles=[angle(A.Vector(*a),A.Vector(*b)) for a in left['normals'] for b in right['normals']]
   probes.append({'epsilonMM':eps,'left':left,'right':right,'signedHeightDifferenceMM':diff,'maxNormalAngleDegrees':max(angles) if angles else None})
  if len(probes)==2:
   limit=(.01*probes[1]['signedHeightDifferenceMM']-.001*probes[0]['signedHeightDifferenceMM'])/.009
   check(f'x{x}/y{y} no finite roof step',abs(limit)<.005)
   rows.append({'xMM':x,'yMM':y,'probes':probes,'extrapolatedSignedStepMM':limit})
  pos=roof(body,x,y);neg=roof(body,-x,y)
  if pos and neg:
   delta=abs(pos['zMM']-neg['zMM']);check(f'x{x}/y{y} mirrored roof',delta<.002);mirror.append({'xMM':x,'yMM':y,'heightDifferenceMM':delta})
 print('Roof station',x,'complete',flush=True)
# Shell samples mirror independently of the top-seam measurements.
shell=Part.makeCompound(body.Shells);gaps=[]
for vertex in body.Vertexes:
 p=vertex.Point;gaps.append(shell.distToShape(Part.Vertex(A.Vector(-p.x,p.y,p.z)))[0])
check('all native boundary vertices mirror onto final shell',max(gaps)<.002)
check('saved source unchanged',sha(source)==before)
report={'status':'fail' if fail else 'pass','blockingFindings':fail,'sourceSHA256':before,'silhouetteJoins':outline,'roofSections':rows,'mirrorRoofSections':mirror,'maxMirroredVertexShellDistanceMM':max(gaps),'maxExtrapolatedRoofStepMM':max(abs(r['extrapolatedSignedStepMM']) for r in rows),'maxNormalAngleAtSmallestEpsilonDegrees':max(p['maxNormalAngleDegrees'] for r in rows for p in r['probes'][-1:] if p['maxNormalAngleDegrees'] is not None),'sourceBytesUnchanged':sha(source)==before,'limits':'Finite local sections test positional continuity by shrinking epsilon; normal-angle measurements identify remaining derivative creases without asserting global curvature continuity. Shape interpretation and human acceptance remain separate.'}
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['silhouetteJoins','roofSections','mirrorRoofSections']},indent=2));A.closeDocument(d.Name);raise SystemExit(bool(fail))
