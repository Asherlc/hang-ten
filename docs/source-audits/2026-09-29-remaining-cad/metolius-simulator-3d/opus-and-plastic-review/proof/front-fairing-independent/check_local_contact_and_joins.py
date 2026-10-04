import sys,json,hashlib,math
from pathlib import Path
import FreeCAD as A
import Part
p=Path(__file__).resolve().parent;source=Path(sys.argv[1]);out=Path(sys.argv[2]);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();h=sha(source);d=A.openDocument(str(source.resolve()));d.recompute();body=d.BodySolid.Shape;contacts={o.ContactID:o.Shape for o in d.Objects if getattr(o,'NodeRole','')=='contact'};fail=[]
def check(k,v):
 if not v:fail.append(k)
def roof(x,y,normals=False):
 hit=body.common(Part.makeLine(A.Vector(x,y,125),A.Vector(x,y,245)))
 if not hit.Vertexes:return None
 z=max(v.Point.z for v in hit.Vertexes);q=A.Vector(x,y,z);ns=[]
 if normals:
  for f in body.Faces:
   b=f.BoundBox
   if x<b.XMin-1e-5 or x>b.XMax+1e-5 or y<b.YMin-1e-5 or y>b.YMax+1e-5 or z<b.ZMin-1e-5 or z>b.ZMax+1e-5:continue
   if f.distToShape(Part.Vertex(q))[0]>.0001:continue
   u,v=f.Surface.parameter(q);n=f.normalAt(u,v)
   if n.z>=0:ns.append([n.x,n.y,n.z])
 return {'zMM':z,'normals':ns}
def angle(a,b):
 a=A.Vector(*a);b=A.Vector(*b);return math.degrees(math.acos(max(-1,min(1,a.dot(b)/(a.Length*b.Length)))))
round_faces=[]
for i,f in enumerate(contacts['round-sloper-3-center'].Faces):
 b=f.optimalBoundingBox();okay=b.XMax<=-47+.002 or b.XMin>=47-.002;round_faces.append({'face':i+1,'xBoundsMM':[b.XMin,b.XMax],'outsideCentralGap':okay});check('roundface outside exactX47gap '+str(i+1),okay)
jug_bounds=contacts['jug-14-center'].optimalBoundingBox();check('jug ends withinX47',jug_bounds.XMin>=-47-.002 and jug_bounds.XMax<=47+.002)
check('jug lower limit remains182.8',jug_bounds.ZMin>=182.8-.002)
roll_membership=[]
for x in [0,30,46]:
 for y in [-90,-92,-93,-93.5,-93.9]:
  hit=roof(x,y)
  if hit is None or hit['zMM']<182.802:continue
  distance=contacts['jug-14-center'].distToShape(Part.Vertex(A.Vector(x,y,hit['zMM'])))[0];check('jug curved nose membership '+str((x,y)),distance<.002);roll_membership.append({'xMM':x,'yMM':y,'zMM':hit['zMM'],'jugDistanceMM':distance})
for x in [0,30,46]:check('jug curved nose witness '+str(x),any(v['xMM']==x for v in roll_membership))
membership=[]
for x in [-47.1,-46.9,-46,-45.6,45.6,46,46.9,47.1]:
 for y in [-35,-50,-80]:
  hit=roof(x,y)
  if hit is None or hit['zMM']<187.001:continue
  point=Part.Vertex(A.Vector(x,y,hit['zMM']));jug=contacts['jug-14-center'].distToShape(point)[0];rnd=contacts['round-sloper-3-center'].distToShape(point)[0];target='jug' if abs(x)<47 else 'round';check('X47membership '+str((x,y)),(jug if target=='jug' else rnd)<.002 and (rnd if target=='jug' else jug)>.02);membership.append({'xMM':x,'yMM':y,'zMM':hit['zMM'],'expected':target,'jugDistanceMM':jug,'roundDistanceMM':rnd})
for x in [-47.1,-46.9,-46,-45.6,45.6,46,46.9,47.1]:check('X47 nonempty roof witness '+str(x),any(v['xMM']==x for v in membership))
print('X47 memberships checked',flush=True)
joins=[]
for label,xs,y in [('nose',[0,15,30,38,42,45.6,46],-80),('flatRoll',[185.1,210,235],-84)]:
 for x in xs:
  probes=[]
  for e in [.01,.001,.0001]:
   a,b=roof(x,y-e,True),roof(x,y+e,True);angles=[angle(aa,bb) for aa in a['normals'] for bb in b['normals']] if a and b else [];probes.append({'epsilonMM':e,'front':a,'rear':b,'heightDifferenceMM':abs(a['zMM']-b['zMM']) if a and b else None,'maximumNormalAngleDegrees':max(angles) if angles else None})
  check(label+' join exists '+str(x),all(v['heightDifferenceMM'] is not None for v in probes))
  if all(v['heightDifferenceMM'] is not None for v in probes):check(label+' no finite step '+str(x),probes[-1]['heightDifferenceMM']<.002)
  joins.append({'kind':label,'xMM':x,'yMM':y,'probes':probes})
print('Join sections checked',flush=True)
shelves=[]
for x in [0,30,46]:
 for wire in body.slice(A.Vector(1,0,0),x):
  for edge in wire.Edges:
   b=edge.BoundBox
   if b.YMin<-94.01 or b.YMax>-79.99 or b.ZMin<182.6 or b.YLength<=.5 or b.ZLength>.0001:continue
   q=edge.valueAt((edge.FirstParameter+edge.LastParameter)/2);top=roof(x,q.y)
   if top and abs(top['zMM']-q.z)<.002:shelves.append({'xMM':x,'yBoundsMM':[b.YMin,b.YMax],'zMM':q.z,'edgeLengthMM':edge.Length})
check('no horizontal nose roof shelf',not shelves)
rolls=[]
for x in [185.1,210,235]:
 probes=[{'yMM':y,'roof':roof(x,y,True)} for y in [-84,-90,-93,-93.9,-93.99,-93.999]];rolls.append({'xMM':x,'probes':probes})
 check('roll reaches forwardedge '+str(x),all(v['roof'] is not None for v in probes))
root_bop=[]
for i,f in enumerate(body.Faces):
 b=f.BoundBox
 side='right' if b.XMin<47<b.XMax and 45<b.XMin else 'left' if b.XMin<-47<b.XMax and b.XMax<-45 else None
 if side is None or b.ZMax<=187:continue
 try:f.check(True);error=None
 except Exception as e:error=repr(e)
 root_bop.append({'face':i+1,'side':side,'error':error});check('root carrier BOP validity '+str(i+1),error is None)
for side in ['left','right']:check('root BOP nonempty '+side,any(v['side']==side for v in root_bop))
check('source bytes unchanged',sha(source)==h)
r={'status':'pass' if not fail else 'fail','blockingFindings':fail,'sourceSHA256':h,'roundContactFaces':round_faces,'rootMembership':membership,'jugForwardRollMembership':roll_membership,'jugBoundsZMM':[jug_bounds.ZMin,jug_bounds.ZMax],'localJoins':joins,'horizontalNoseRoofShelves':shelves,'flatForwardRolls':rolls,'rootCarrierBOPChecks':root_bop,'sourceBytesUnchanged':sha(source)==h,'limits':['ContactboundaryX47 and localjoin locations validate authored intent, not maker coordinates.','Finite normal-angle samples are reported rather than assumed globallyC1; visible/functional acceptance remains Opus/user decision.','The0.002mm existing native surface tolerance is retained forcontact/step checks; no publishedfact tolerance was relaxed.']};out.write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);print(json.dumps({'status':r['status'],'blockingFindings':fail,'report':str(out)},indent=2));raise SystemExit(bool(fail))
