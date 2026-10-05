import FreeCAD as A,Part,json,hashlib
from pathlib import Path
w=Path(__file__).resolve().parent;p=w.parent/'candidate/metolius-simulator-3d.FCStd';d=A.openDocument(str(p));d.recompute();body=d.BodySolid.Shape;rows=[]
for x,label in [(0,'Center jug center'),(30,'Center jug side'),(46,'Center jug root'),(95,'Round sloper core'),(148.1,'Round-flat join'),(210,'Flat sloper core'),(185.1,'Flat blend end'),(235,'Flat outer core'),(293,'Outer jug center')]:
 plane=Part.Face(Part.makePolygon([A.Vector(x,-110,-5),A.Vector(x,20,-5),A.Vector(x,20,255),A.Vector(x,-110,255),A.Vector(x,-110,-5)]))
 loops=[[[[v.y,v.z] for v in e.discretize(Deflection=.05)] for e in body.section(plane).Edges]]
 contacts=[]
 for o in d.Objects:
  if getattr(o,'NodeRole','')!='contact':continue
  lines=o.Shape.section(Part.Face(Part.makePolygon([A.Vector(x,-110,-5),A.Vector(x,20,-5),A.Vector(x,20,255),A.Vector(x,-110,255),A.Vector(x,-110,-5)]))).Edges
  if lines:contacts.append({'id':o.ContactID,'edges':[[[v.y,v.z] for v in e.discretize(Deflection=.05)] for e in lines]})
 rows.append({'xMm':x,'label':label,'bodyLoops':loops,'contacts':contacts})
r={'sourceSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'axis':'Y=0 rear wall; negative Y forward; Z up','sections':rows,'topContacts':{o.ContactID:{'ymin':o.Shape.optimalBoundingBox().YMin,'ymax':o.Shape.optimalBoundingBox().YMax} for o in d.Objects if getattr(o,'NodeRole','')=='contact' and any(k in o.ContactID for k in ['sloper','jug'])}}
v,t=body.tessellate(.28);(w/'native-body-mesh.json').write_text(json.dumps({'p':[[p.x,p.y,p.z] for p in v],'t':t}))
(w/'native-sections.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k!='sections'})
