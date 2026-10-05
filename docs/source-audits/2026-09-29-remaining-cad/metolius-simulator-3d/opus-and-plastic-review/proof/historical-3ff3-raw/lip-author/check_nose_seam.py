import FreeCAD as A,Part,json,hashlib
from pathlib import Path
w=Path(__file__).resolve().parent;p=w/'probe-source.FCStd';d=A.openDocument(str(p));d.recompute();s=d.BodySolid.Shape;r={'sourceSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':[]}
for x in [0,15,30,38,42,46]:
 row={'x':x,'samples':[]}
 for e in [.01,.001,.0001]:
  heights=[]
  for y in [-80-e,-80+e]:
   hit=s.common(Part.makeLine(A.Vector(x,y,160),A.Vector(x,y,230)));assert hit.Vertexes;heights.append(max(v.Point.z for v in hit.Vertexes))
  row['samples'].append({'epsilonMm':e,'heightsMm':heights,'deltaMm':abs(heights[0]-heights[1])})
 r['rows'].append(row)
r['status']='pass' if all(v['samples'][-1]['deltaMm']<.002 for v in r['rows']) else 'fail';(w/'nose-seam-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));assert r['status']=='pass'
