import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'probe-source.FCStd'));d.recompute();s=d.BodySolid.Shape
r={'default':str(s.optimalBoundingBox()),'bounds':str(s.BoundBox),'maxTolerance':s.getTolerance(1)}
for args in [(False,False),(False,True),(True,False),(True,True)]:
 try:r[str(args)]=str(s.optimalBoundingBox(*args))
 except Exception as e:r[str(args)]=str(e)
(w/'envelope-probe.json').write_text(json.dumps(r,indent=2));print(r)
