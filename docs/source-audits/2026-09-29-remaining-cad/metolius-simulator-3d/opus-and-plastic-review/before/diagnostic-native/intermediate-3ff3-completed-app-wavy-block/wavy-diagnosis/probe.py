import FreeCAD as A,Part,json,hashlib,math
from pathlib import Path
w=Path(__file__).resolve().parent
paths={"current":Path("Hangboards/metolius-simulator-3d/metolius-simulator-3d.FCStd"),"original":Path(".context/placid-badger/metolius-simulator-3d-functional-lip-correction/original-9449/metolius-simulator-3d.FCStd")}
report={}
for name,path in paths.items():
 before=hashlib.sha256(path.read_bytes()).hexdigest();d=A.openDocument(str(path.resolve()));s=d.ContinuousFrontRelief
 rows=[]
 for i,g in enumerate(s.Geometry):
  if not isinstance(g,Part.BSplineCurve):continue
  samples=[]
  for j in range(101):
   u=g.FirstParameter+(g.LastParameter-g.FirstParameter)*j/100;p=g.value(u);t=g.tangent(u)[0]
   samples.append({"yz":[p.x,p.y],"tangentYZ":[t.x,t.y],"frontNormalTiltDegrees":math.degrees(math.atan2(t.x,-t.y))})
  rows.append({"geometryIndex":i,"degree":g.Degree,"polesYZ":[[p.x,p.y] for p in g.getPoles()],"samples":samples})
 result={"sourceSHA256":before,"profileName":s.Name,"placement":str(s.Placement),"reliefPrismDirection":list(d.ReliefPrism.Dir),"reliefPrismWidth":d.ReliefPrism.LengthFwd.Value,"curves":rows}
 if name=="current":
  sections={}
  for x in [0,40,100,210]:
   plane=Part.makePlane(120,240,A.Vector(x,10,-5),A.Vector(1,0,0));plane=Part.makePolygon([A.Vector(x,10,-5),A.Vector(x,-110,-5),A.Vector(x,-110,235),A.Vector(x,10,235),A.Vector(x,10,-5)]);face=Part.Face(plane)
   sect=d.BodySolid.Shape.section(face);sections[str(x)]=[[[p.y,p.z] for p in e.discretize(Deflection=.05)] for e in sect.Edges]
  result["bodySectionsYZMM"]=sections
 A.closeDocument(d.Name);result["sourceUnchanged"]=hashlib.sha256(path.read_bytes()).hexdigest()==before;report[name]=result
report["profileExactEqualToOriginal"]=report["current"]["curves"]==report["original"]["curves"]
(w/"native-relief-diagnosis.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"currentSource":report["current"]["sourceSHA256"],"profileExactEqualToOriginal":report["profileExactEqualToOriginal"],"curves":[{"poles":r["polesYZ"],"normalTiltRange":[min(p["frontNormalTiltDegrees"] for p in r["samples"]),max(p["frontNormalTiltDegrees"] for p in r["samples"])]} for r in report["current"]["curves"]]},indent=2))
