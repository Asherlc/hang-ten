import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));d.recompute();r=[]
for label,box in [('jug',d.RegionBounds_jug_14_center.Shape),('roundright',Part.makeBox(101,65,70,A.Vector(47,-94,145)))]:
 c=d.BodySolid.Shape.common(box);bb=c.optimalBoundingBox() if c.Faces else None;r.append({'label':label,'valid':c.isValid(),'solidCount':len(c.Solids),'bounds':str(bb),'faces':[{'bounds':str(f.optimalBoundingBox()),'surface':type(f.Surface).__name__} for f in c.Faces]})
(w/'solid-clip-probe.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
