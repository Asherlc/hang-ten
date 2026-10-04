import FreeCAD as A,Part,json,hashlib
from pathlib import Path
w=Path(__file__).resolve().parent;p=w/'probe-source.FCStd';d=A.openDocument(str(p));d.recompute();shape=d.BodySolid.Shape;box=Part.makeBox(94,93.999,35.009,A.Vector(-47,-94,187.001));r={'sourceSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'faces':[]}
for i,f in enumerate(shape.Faces):
 b=f.optimalBoundingBox()
 if b.XMin>45 and b.XMax<62 and b.ZMax>190:
  row={'face':i+1,'bounds':str(b)}
  try:f.check(True);row['bopCheck']='pass'
  except Exception as e:row['bopCheck']=str(e)
  c=f.common(box);row['clipArea']=c.Area;row['clipBounds']=str(c.optimalBoundingBox()) if c.Faces else None;row['clipValid']=c.isValid();r['faces'].append(row)
s=shape.common(box);r['solidClip']={'valid':s.isValid(),'solids':len(s.Solids),'volume':s.Volume,'bounds':str(s.optimalBoundingBox()) if s.Faces else None};r['status']='pass' if all(x['bopCheck']=='pass' and x['clipArea']>1 for x in r['faces']) and len(s.Solids)==1 and s.Volume>0 else 'fail';(w/'repaired-root-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));assert r['status']=='pass'
