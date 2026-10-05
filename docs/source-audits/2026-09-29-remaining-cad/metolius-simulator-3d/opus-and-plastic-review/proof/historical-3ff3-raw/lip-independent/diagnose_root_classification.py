import json,hashlib
from pathlib import Path
import FreeCAD as A
import Part
p=Path(__file__).resolve().parent;source=p/'diagnostic-ec348.FCStd';h=hashlib.sha256(source.read_bytes()).hexdigest();d=A.openDocument(str(source));d.recompute();body=d.BodySolid.Shape;box=d.RegionBounds_jug_14_center.Shape;rows=[]
for i,f in enumerate(body.Faces):
 b=f.BoundBox
 if not (45.4<abs(b.XMin)<61.1 and 45.4<abs(b.XMax)<61.1 and b.XLength>10 and b.ZMax>187):continue
 row={'face':i+1,'orientation':f.Orientation,'surfaceType':type(f.Surface).__name__,'bounds':[b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax],'area':f.Area,'valid':f.isValid()}
 try:row['bopCheck']=str(f.check(True))
 except Exception as e:row['bopCheckError']=repr(e)
 rev=f.copy();rev.reverse();clips=[]
 for name,shape in [('original',f),('reversedCopy',rev)]:
  clipped=shape.common(box);clips.append({'case':name,'area':clipped.Area,'faces':len(clipped.Faces),'valid':clipped.isValid()})
 row['clips']=clips;row['boxSectionEdges']=len(f.section(box).Edges);samples=[];u0,u1,v0,v1=f.ParameterRange
 for fu,fv in [(.1,.2),(.5,.5),(.9,.8)]:
  u=u0+(u1-u0)*fu;v=v0+(v1-v0)*fv
  if not f.isPartOfDomain(u,v):continue
  point=f.valueAt(u,v);n=f.normalAt(u,v);n.normalize();entry={'point':[point.x,point.y,point.z],'normal':[n.x,n.y,n.z],'insideWitnesses':[]}
  for eps in [.05,.5]:entry['insideWitnesses'].append({'offsetMM':eps,'plusNormalInside':body.isInside(point+n*eps,1e-7,False),'minusNormalInside':body.isInside(point-n*eps,1e-7,False)})
  samples.append(entry)
 row['samples']=samples;rows.append(row);print('rootface',i+1,'checked',flush=True)
r={'sourceSHA256':h,'bodyOrientation':body.Orientation,'bodyVolumeMM3':body.Volume,'bodyValid':body.isValid(),'rootFaces':rows,'sourceBytesUnchanged':hashlib.sha256(source.read_bytes()).hexdigest()==h,'scope':'Independent native classification diagnosis on immutableec348; reversed copies are diagnostic only, never exported or saved.'};(p/'root-classification-diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
