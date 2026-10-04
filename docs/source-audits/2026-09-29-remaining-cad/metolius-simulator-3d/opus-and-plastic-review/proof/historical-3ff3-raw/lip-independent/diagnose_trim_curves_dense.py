import FreeCAD as A,Part,json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent;src=p.parent/'probe-source.FCStd';h=hashlib.sha256(src.read_bytes()).hexdigest();d=A.openDocument(str(src));d.recompute();r={'sourceSHA256':h,'objects':[]}
def xyz(q):return [q.x,q.y,q.z]
for name in ['CenterShoulderBoundedTransition','ShellWithContinuousShoulders','BodySolid']:
 o=d.getObject(name)
 if not o:continue
 row={'name':name,'type':o.TypeId,'inputs':[x.Name for x in o.InList],'faces':[]}
 for i,f in enumerate(o.Shape.Faces):
  b=f.optimalBoundingBox()
  if not (45<b.XMin<47<b.XMax<62 and b.ZMax>190):continue
  fr={'face':i+1,'bounds':str(b),'edges':[]}
  try:f.check(True);fr['bop']='pass'
  except Exception as e:fr['bop']=str(e)
  for j,e in enumerate(f.Edges):
   er={'edge':j+1,'bounds':str(e.optimalBoundingBox()),'length':e.Length,'orientation':e.Orientation,'tolerance':e.getTolerance(1),'curveType':type(e.Curve).__name__,'range':[e.FirstParameter,e.LastParameter]}
   try:e.check(True);er['edgeBOP']='pass'
   except Exception as ex:er['edgeBOP']=str(ex)
   try:
    result=f.curveOnSurface(e);er['pcurveReturnTypes']=[type(x).__name__ for x in result];c,lo,hi=result
    er['pcurveRange']=[lo,hi];samples=[]
    for k in range(201):
     t=lo+(hi-lo)*k/200;uv=c.value(t);q=f.Surface.value(uv.x,uv.y);v=e.Curve.value(t);samples.append({'fraction':k/200,'parameter':t,'uv':[uv.x,uv.y],'point3D':xyz(v),'surfacePoint':xyz(q),'distanceMM':(q-v).Length})
    er['maximumSameParameterDeviationMM']=max(x['distanceMM'] for x in samples);er['samples']=samples
   except Exception as ex:er['pcurveError']=repr(ex)
   fr['edges'].append(er)
  row['faces'].append(fr)
 r['objects'].append(row)
r['sourceBytesUnchanged']=hashlib.sha256(src.read_bytes()).hexdigest()==h;(p/'trim-curve-diagnosis-dense.json').write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);print(json.dumps({'source':h,'objects':len(r['objects'])}))
