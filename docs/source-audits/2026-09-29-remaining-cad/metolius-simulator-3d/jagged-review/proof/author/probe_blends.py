import sys,json,math
from pathlib import Path
import FreeCAD as A, Part
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author'
d=A.openDocument(str(w/'before/metolius-simulator-3d.FCStd'));d.recompute();base=d.getObject('ShellWithDistinctSlopers');edges=[]
for i,e in enumerate(base.Shape.Edges):
 b=e.BoundBox
 if b.XLength<1e-5 and any(abs(abs(b.XMin)-x)<1e-4 for x in [47,148,258]) and b.YLength>10 and b.ZMin>149:
  edges.append(i+1)
print('EDGES',edges,flush=True)
rows=[]
for radius in [6.,3.,1.]:
 try:
  shape=base.Shape.makeFillet(radius,[base.Shape.Edges[i-1] for i in edges]);valid=shape.isValid()
  row={'radius':radius,'valid':valid,'solidCount':len(shape.Solids),'faces':len(shape.Faces)}
  if valid:
   shape.exportBrep(str(w/('probe-'+str(radius)+'.brep')))
  rows.append(row)
 except Exception as e:rows.append({'radius':radius,'error':str(e)})
print(json.dumps(rows,indent=2));(w/'probe-blends.json').write_text(json.dumps({'edges':edges,'results':rows},indent=2)+'\n');A.closeDocument(d.Name)
