import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;r={}
for label,p in [('before',w/'frozen-3ff3/metolius-simulator-3d.FCStd'),('candidate',w/'candidate/metolius-simulator-3d.FCStd')]:
 d=A.openDocument(str(p));s=d.BodySolid.Shape;rows={}
 for a,b in [(False,False),(False,True),(True,False),(True,True)]:
  bb=s.optimalBoundingBox(a,b);rows[str((a,b))]=[bb.XLength,bb.YLength,bb.ZLength]
 r[label]={'boundsModes':rows,'tolerances':[s.getTolerance(i) for i in range(3)]};A.closeDocument(d.Name)
(w/'bounds-diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
