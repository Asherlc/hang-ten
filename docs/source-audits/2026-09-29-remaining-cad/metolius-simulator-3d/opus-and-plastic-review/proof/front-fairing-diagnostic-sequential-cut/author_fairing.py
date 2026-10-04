import FreeCAD as A,Part,Sketcher,json,hashlib,sys,math
from pathlib import Path
w=Path(__file__).resolve().parent;root=Path.cwd();sys.path.insert(0,str(root/".context/placid-badger/cad-wall-boards"));from author_wall import bezier
source=w/"frozen-3ff3/metolius-simulator-3d.FCStd";d=A.openDocument(str(source));d.recompute();manifest=d.HangTenBoardManifest;originalBody=d.BodySolid.Shape.copy();s=d.ContinuousFrontRelief
for o in list(reversed(d.Objects)):
 if o.Name.startswith(("Contact_","Surface_","LocalSurface_","RegionBounds_")) or o.Name in ["RoundSloperPairedShoulders","RoundSloperCenterGap"]:d.removeObject(o.Name)
ge=[g.copy() for g in s.Geometry[:2]]
for g in s.Geometry:
 if not isinstance(g,Part.BSplineCurve):continue
 a=g.value(g.FirstParameter);b=g.value(g.LastParameter)
 if b.y>=135:ge.append(g.copy())
 elif a.y>135:
  lo,hi=g.FirstParameter,g.LastParameter
  for _ in range(60):
   mid=(lo+hi)/2
   if g.value(mid).y>135:lo=mid
   else:hi=mid
  trim=g.copy();trim.segment(g.FirstParameter,(lo+hi)/2);ge.append(trim)
# Operator-authored cubic Hermite taper. Exact existing depth stations retained.
# Shared derivative dy/dz deliberately avoids repeated zero slope at each row.
stations=[(-72.128,135.,-.528),(-65.,117.,-.35),(-55.,87.,-.364),(-44.,59.,-.394),(-32.,29.,-.414),(-18.,-4.,-.43)]
curves=[]
for (y0,z0,m0),(y1,z1,m1) in zip(stations,stations[1:]):
 dz=z1-z0;poles=[(y0,z0),(y0+m0*dz/3,z0+dz/3),(y1-m1*dz/3,z1-dz/3),(y1,z1)];assert all(poles[i][0]<poles[i+1][0] for i in range(3));g=bezier(poles);ge.append(g);curves.append(g)
ge.append(Part.LineSegment(A.Vector(-18,-4,0),A.Vector(0,-4,0)))
for i in reversed(range(s.ConstraintCount)):s.delConstraint(i)
for i in reversed(range(s.GeometryCount)):s.delGeometry(i)
for g in ge:i=s.addGeometry(g,False);s.addConstraint(Sketcher.Constraint("Block",i))
# Isolate the two existing small central pocket cutters from the compound BOP.
# No cutter geometry or scalar depth is altered by this native dependency repair.
base=d.BodySolid.Base;small=[d.Cutter_pocket_13_left,d.Cutter_pocket_13_right]
d.PocketCutters.Links=[o for o in d.PocketCutters.Links if o not in small]
main=d.addObject('Part::Cut','MainCavityCut');main.Base=base;main.Tool=d.PocketCutters;main.Refine=False
left=d.addObject('Part::Cut','SmallCenterPocketLeftCut');left.Base=main;left.Tool=small[0];left.Refine=False
d.BodySolid.Base=left;d.BodySolid.Tool=small[1]
d.recompute();body=d.BodySolid.Shape;assert body.isValid() and len(body.Solids)==1 and body.Volume>0
upper=Part.makeBox(800,140,120,A.Vector(-400,-110,135));a=originalBody.common(upper);b=body.common(upper);upperDiff=[a.cut(b).Volume,b.cut(a).Volume];assert max(upperDiff)<1e-5,upperDiff
samples=[]
for g in curves:
 for i in range(101):
  u=g.FirstParameter+(g.LastParameter-g.FirstParameter)*i/100;p=g.value(u);t=g.tangent(u)[0];samples.append({"yz":[p.x,p.y],"tiltDegrees":math.degrees(math.atan2(t.x,-t.y))})
assert d.HangTenBoardManifest==manifest;assert s.FullyConstrained
out=w/"probe-source.FCStd";d.saveAs(str(out));p,t=body.tessellate(.28);(w/"probe-native-body-mesh.json").write_text(json.dumps({"p":[[v.x,v.y,v.z] for v in p],"t":t}))
r={"sourceSHA256":hashlib.sha256(out.read_bytes()).hexdigest(),"beforeSourceSHA256":hashlib.sha256(source.read_bytes()).hexdigest(),"status":"native-shape-probe-pass-contacts-pending","frontFairingStationsYZAndDyDz":stations,"upperProtectedZMinimumMM":135,"upperBodyBidirectionalDifferenceVolumesMM3":upperDiff,"finalSolidValid":body.isValid(),"solidCount":len(body.Solids),"volumeMM3":body.Volume,"fullyConstrainedRelief":s.FullyConstrained,"rawManifestUnchanged":d.HangTenBoardManifest==manifest,"nativeSamples":samples,"displayEstimate":"Author-selected shared slopes; original depth station positions retained. Complete primary images reviewed without measurement.","existingGripFeatures":"Unchanged above Z135; same forward sloper profiles, center crest/return/nose, roof joins and semantic bounds."}
(w/"probe-design.json").write_text(json.dumps(r,indent=2)+"\n");print(json.dumps({k:v for k,v in r.items() if k!="nativeSamples"},indent=2));A.closeDocument(d.Name)
