import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));d.recompute();r={'commonProperties':d.LocalSurface_jug_14_center_0.PropertiesList,'cutProperties':d.RoundSloperPairedShoulders.PropertiesList,'rows':[]}
shape=d.BodySolid.Shape;box=d.RegionBounds_jug_14_center.Shape
for i,f in enumerate(shape.Faces):
 b=f.optimalBoundingBox()
 if b.XMin>45 and b.XMax<62 and b.ZMax>190:
  row={'face':i+1,'bounds':[b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax],'clips':[]}
  for tol in [0,1e-7,1e-6,1e-5,.0001,.001]:
   c=f.common(box,tol);q=c.optimalBoundingBox() if c.Faces else None;row['clips'].append({'tol':tol,'faces':len(c.Faces),'area':c.Area,'bounds':str(q)})
  r['rows'].append(row)
(w/'contact-clip-probe.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
