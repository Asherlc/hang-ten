import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));d.recompute();f=d.BodySolid.Shape.Faces[11];r=[]
boxes={'full':d.RegionBounds_jug_14_center.Shape,'x':Part.makeBox(94,300,300,A.Vector(-47,-150,0)),'y':Part.makeBox(800,93.999,300,A.Vector(-400,-94,0)),'z':Part.makeBox(800,300,35.009,A.Vector(-400,-150,187.001))}
for order in [('x',),('y',),('z',),('x','y','z'),('y','x','z'),('z','x','y')]:
 c=f
 for key in order:c=c.common(boxes[key])
 r.append({'order':order,'area':c.Area,'faces':len(c.Faces),'bounds':str(c.optimalBoundingBox()) if c.Faces else None})
(w/'sequential-clip-probe.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
