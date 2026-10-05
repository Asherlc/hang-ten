"""Read actual committed/exported USDZ; validate only operator-selected regions."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,zipfile
import numpy as np
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from pxr import Usd,UsdGeom,UsdShade
sys.path.insert(0,str(Path("Tools/HangboardCAD").resolve()))
from usdz_writer import read_usdz
BASE=Path(".context/placid-badger/nug-pinch-review/independent-geometry-validation")
PACKAGE=Path("Hangboards/frictitious-nug")
BEFORE=Path(".context/placid-badger/nug-pinch-review/native-author/before/assets/primary.usdz")
ASSET=PACKAGE/"assets/primary.usdz"
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected={"assets/primary.usdz":"9b24f881059a7d79afd3b676da6324b3d0d65fb0977e2eab100b88bfa5a5e800","assets/primary.model.json":"c6ecc298e414726f5b543de89d7e22ee6d6180ff56dd71777f71a95624db3a9e","suspension.json":"8a3fdf291c1ef34588425a4a7a73524fab33abdbb5a561456d571ecdd86642fc"}
assert all(sha(PACKAGE/name)==digest for name,digest in expected.items())
sourceSHA=sha(PACKAGE/"frictitious-nug.FCStd");assert sourceSHA.startswith("03ae5ece")
assert sha(BEFORE)=="1dc1b6c1198a71e62477dc1bbf7b6404d19324d06d438b5a4c60958636bf017f"
before=read_usdz(BEFORE);current=read_usdz(ASSET)
descriptor=json.loads((PACKAGE/"assets/primary.model.json").read_text())
assert len(current["nodes"])==7
assert set(current["nodes"])=={x["nodeID"] for x in descriptor["nodes"]}
assert set(descriptor["contacts"])=={"jug-40","pinch-60","edge-20","edge-25","edge-13","edge-8"}
assert descriptor["contacts"]["pinch-60"]["nodeIDs"]==["nug_jug_40","nug_pinch_60"]
assert next(n for n in descriptor["nodes"] if n["nodeID"]=="nug_jug_40")=={"nodeID":"nug_jug_40","role":"contact","contactID":"jug-40","additionalContactIDs":["pinch-60"]}
unchanged={}
for name in ["nug_jug_40","nug_edge_13","nug_edge_20","nug_edge_25","nug_edge_8"]:
 a=before["nodes"][name];c=current["nodes"][name]
 for key in ["points_m","normals","triangles"]:assert a[key]==c[key],(name,key)
 unchanged[name]={"vertices":len(c["points_m"]),"triangles":len(c["triangles"]),"pointsNormalsFacesExact":True}
# The USDZ stores float32 coordinates; bound rectangle area error by its
# perimeter times the same 10 nm positional tolerance (plus corner terms).
spatialTolerance=1e-8
areaTolerance=2*(.094+.009)*spatialTolerance+4*spatialTolerance**2
n=current["nodes"]["nug_pinch_60"];vertices=np.asarray(n["points_m"]);groups={"original-lower-cap":[]}
for side in ["front","rear"]:
 for level in ["upper","lower"]:groups[f"{side}-{level}"]=[]
for index,ids in enumerate(n["triangles"]):
 tri=vertices[list(ids)];assert np.all(np.abs(tri[:,0])<=.047+spatialTolerance)
 if np.all(tri[:,1]>=-.03-spatialTolerance) and np.all(tri[:,1]<=-.027+spatialTolerance):
  groups["original-lower-cap"].append(index);continue
 match=[]
 for side,z in [("front",.02),("rear",-.02)]:
  for level,lo,hi in [("upper",.018,.027),("lower",-.027,-.018)]:
   if np.all(np.abs(tri[:,2]-z)<=spatialTolerance) and np.all(tri[:,1]>=lo-spatialTolerance) and np.all(tri[:,1]<=hi+spatialTolerance):match.append(f"{side}-{level}")
 assert len(match)==1,(index,tri.tolist(),match)
 groups[match[0]].append(index)
def oriented_faces(node,indices):
 v=node["points_m"]
 return Counter(tuple(tuple(v[i]) for i in node["triangles"][j]) for j in indices)
# Same triangle winding and vertex coordinates for every original lower-cap face.
assert oriented_faces(n,groups["original-lower-cap"])==oriented_faces(before["nodes"]["nug_pinch_60"],range(len(before["nodes"]["nug_pinch_60"]["triangles"])))
returns={}
for key,indices in groups.items():
 if key=="original-lower-cap":continue
 assert len(indices)==4,(key,len(indices))
 polygons=[Polygon(vertices[list(n["triangles"][i])][:,:2]) for i in indices]
 union=unary_union(polygons);total=sum(p.area for p in polygons)
 lo,hi=(.018,.027) if key.endswith("upper") else (-.027,-.018)
 expectedRectangle=box(-.047,lo,.047,hi)
 symmetricDifference=union.symmetric_difference(expectedRectangle).area
 assert abs(union.area-.000846)<=areaTolerance,(key,union.area)
 assert abs(total-union.area)<=1e-14,(key,"overlapping triangles")
 assert symmetricDifference<=areaTolerance,(key,symmetricDifference)
 returns[key]={"triangles":len(indices),"triangleAreaM2":total,"unionAreaM2":union.area,"expectedAreaM2":.000846,"overlapAreaM2":total-union.area,"symmetricDifferenceFrom94x9mmRectangleM2":symmetricDifference}
assert sum(len(v) for k,v in groups.items() if k!="original-lower-cap")==16
stage=Usd.Stage.Open(str(ASSET));materialPrims=[];shaderPrims=[];materialRelationships=[];uvNodes=[]
for prim in stage.Traverse():
 if prim.IsA(UsdShade.Material):materialPrims.append(str(prim.GetPath()))
 if prim.IsA(UsdShade.Shader):shaderPrims.append(str(prim.GetPath()))
 for rel in prim.GetRelationships():
  if rel.GetName().startswith("material:binding"):materialRelationships.append(str(rel.GetPath()))
 if prim.IsA(UsdGeom.Mesh) and UsdGeom.PrimvarsAPI(prim).HasPrimvar("st"):uvNodes.append(str(prim.GetPath()))
assert not(materialPrims or shaderPrims or materialRelationships)
assert not current["materials"] and all(n["material"] is None for n in current["nodes"].values())
with zipfile.ZipFile(ASSET) as z:members=z.namelist()
assert all(Path(m).suffix.lower() in [".usdc",".usda",".usd"] for m in members),members
body=np.asarray(current["nodes"]["nug_body"]["points_m"])
allPoints=np.concatenate([np.asarray(n["points_m"]) for n in current["nodes"].values()])
for bounds in [body,allPoints]:
 assert np.allclose(bounds.min(axis=0),[-.065,-.03,-.02],atol=spatialTolerance,rtol=0)
 assert np.allclose(bounds.max(axis=0),[.065,.03,.02],atol=spatialTolerance,rtol=0)
report={"status":"passed","sourceSHA256":sourceSHA,"assetSHA256":sha(ASSET),"descriptorSHA256":sha(PACKAGE/"assets/primary.model.json"),"sidecarSHA256":sha(PACKAGE/"suspension.json"),"beforeAssetSHA256":sha(BEFORE),"unchangedNodes":unchanged,"nodeCount":7,"logicalContacts":sorted(descriptor["contacts"]),"pinchMembership":["nug_jug_40","nug_pinch_60"],"primaryPinchTriangles":len(n["triangles"]),"originalLowerCapTriangles":len(groups["original-lower-cap"]),"originalLowerCapTriangleCoordinatesAndWindingExact":True,"approvedReturns":returns,"allPrimaryPinchTrianglesClassified":True,"noOtherHighlightSurface":True,"spatialToleranceMeters":spatialTolerance,"areaToleranceM2":areaTolerance,"bodyBoundsMeters":{"min":body.min(axis=0).tolist(),"max":body.max(axis=0).tolist()},"allMeshBoundsMeters":{"min":allPoints.min(axis=0).tolist(),"max":allPoints.max(axis=0).tolist()},"materials":{"materialPrims":materialPrims,"shaderPrims":shaderPrims,"bindingRelationships":materialRelationships,"uvNodes":uvNodes,"archiveMembers":members},"scope":"Numerical verification of operator-selected native contact surfaces only; no physical shape generation/judgment, compiler execution or cord solve.","scriptSHA256":sha(__file__)}
assert all(sha(PACKAGE/name)==digest for name,digest in expected.items()) and sha(PACKAGE/"frictitious-nug.FCStd")==sourceSHA
(BASE/"final-coverage-verification.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
