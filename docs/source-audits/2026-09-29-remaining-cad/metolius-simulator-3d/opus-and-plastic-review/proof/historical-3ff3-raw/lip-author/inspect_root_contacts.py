import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));d.recompute();r={}
for name in ['Contact_jug_14_center','Contact_round_sloper_3_center','RoundSloperPairedShoulders']:
 o=d.getObject(name);b=o.Shape.optimalBoundingBox();rows=[]
 for f in o.Shape.Faces:
  q=f.optimalBoundingBox();rows.append({'area':f.Area,'bounds':[q.XMin,q.XMax,q.YMin,q.YMax,q.ZMin,q.ZMax]})
 r[name]={'bounds':[b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax],'faces':rows}
(w/'root-contact-diagnosis.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
