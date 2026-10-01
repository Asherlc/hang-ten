import json,hashlib,math
from pathlib import Path
import FreeCAD as A
import Part
p=Path(__file__).resolve().parent;source=p.parent/'candidate/metolius-simulator-3d.FCStd';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();h=sha(source);d=A.openDocument(str(source));d.recompute();body=d.getObject('BodySolid');params=d.getObject('Parameters');original=body.Shape.copy();params.Depth_edge_11_left=16;d.recompute();params.Depth_edge_11_left=14;d.recompute();restored=body.Shape.copy();errors=[];print('Edit and restore complete',flush=True)
def box(s):
 b=s.BoundBox;return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
def flatten(v):
 if hasattr(v,'x'):return [float(v.x),float(v.y),float(v.z)]
 if isinstance(v,(list,tuple)):return [n for x in v for n in flatten(x)]
 return [float(v)]
def controls(f):
 s=f.Surface;r={'type':type(s).__name__,'parameterRange':list(f.ParameterRange),'orientation':f.Orientation}
 for name in ['getPoles','getWeights','getUKnots','getVKnots','getUMultiplicities','getVMultiplicities']:
  if hasattr(s,name):r[name]=flatten(getattr(s,name)())
 for name in ['UDegree','VDegree','Radius','MajorRadius','MinorRadius','Axis','Center','Position']:
  if hasattr(s,name):r[name]=flatten(getattr(s,name))
 return r
rows=[];restored_faces=list(restored.Faces);restored_boxes=[box(f) for f in restored_faces];restored_types=[type(f.Surface) for f in restored_faces];unused=set(range(len(restored_faces)))
for idx,a in enumerate(original.Faces):
 a_box=box(a);a_type=type(a.Surface)
 candidates=[j for j in unused if a_type==restored_types[j]]
 if not candidates:errors.append('no matching surface type '+str(idx));continue
 j=min(candidates,key=lambda k:max(abs(x-y) for x,y in zip(a_box,restored_boxes[k])));b=restored_faces[j];unused.remove(j)
 bound=max(abs(x-y) for x,y in zip(box(a),box(b)));ca,cb=controls(a),controls(b);delta=0.;controlsMatch=True
 for k in ca:
  if isinstance(ca[k],list):
   if len(ca[k])!=len(cb.get(k,[])):controlsMatch=False;continue
   delta=max(delta,max((abs(x-y) for x,y in zip(ca[k],cb[k])),default=0))
  elif ca[k]!=cb.get(k):controlsMatch=False
 samples=[]
 for origin,target in [(a,b),(b,a)]:
  u0,u1,v0,v1=origin.ParameterRange
  for fu,fv in [(.23,.31),(.5,.5),(.77,.69)]:
   u=u0+(u1-u0)*fu;v=v0+(v1-v0)*fv
   if not origin.isPartOfDomain(u,v):continue
   if not target.isPartOfDomain(u,v):errors.append('trim domain mismatch face '+str(idx));continue
   point=origin.valueAt(u,v);dist=(point-target.valueAt(u,v)).Length;na=origin.normalAt(u,v);nb=target.normalAt(u,v);angle=math.degrees(math.acos(max(-1,min(1,na.dot(nb)/(na.Length*nb.Length)))))
   samples.append({'distanceMM':dist,'normalAngleDegrees':angle})
  target_vertices=[v.Point for v in target.Vertexes]
  for vertex in origin.Vertexes:samples.append({'distanceMM':min((vertex.Point-point).Length for point in target_vertices),'normalAngleDegrees':None})
 md=max((s['distanceMM'] for s in samples),default=0);ma=max((s['normalAngleDegrees'] or 0 for s in samples),default=0)
 row={'originalFace':idx,'restoredFace':j,'surfaceType':ca['type'],'maximumBoundsDifferenceMM':bound,'numericControlFieldsMatch':controlsMatch,'maximumControlDifference':delta,'samples':len(samples),'maximumSurfaceDistanceMM':md,'maximumNormalAngleDegrees':ma};rows.append(row)
 if bound>1e-7 or not controlsMatch or delta>1e-7 or md>1e-6 or ma>1e-4:errors.append('surface equivalence face '+str(idx))
 if idx%25==0:print('checked face',idx,flush=True)
errors+=['unmatched restored faces'] if unused else []
r={'status':'pass' if not errors else 'fail','blockingFindings':errors,'sourceSHA256':h,'sourceBytesUnchanged':sha(source)==h,'faceCount':len(rows),'rows':rows,'maximumSurfaceDistanceMM':max(r['maximumSurfaceDistanceMM'] for r in rows),'maximumNormalAngleDegrees':max(r['maximumNormalAngleDegrees'] for r in rows),'maximumControlDifference':max(r['maximumControlDifference'] for r in rows),'sampleCount':sum(r['samples'] for r in rows),'scope':'Both directions; matched native vertices and corresponding valueAt/normalAt at three UV fractions inside both trimmed domains. Corresponding-point separation upper-bounds actual surface distance, avoids inverse projection, and is meaningful only with matching native controls/ranges/orientation. Cached surface-type/bounds matching avoids repeated all-face surface construction. Compare poles/weights/knots/multiplicities/degrees/radii/axes/origins. No scalar volume tolerance was changed.'};(p/'restore-surface-witness.json').write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));raise SystemExit(bool(errors))
