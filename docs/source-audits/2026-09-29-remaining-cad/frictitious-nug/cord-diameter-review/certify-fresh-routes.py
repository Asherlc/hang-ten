import copy,hashlib,json,sys
from pathlib import Path
import numpy as np,trimesh
sys.path.insert(0,"Tools/HangboardCAD")
from native_cord_routes import checked_clearance,length
from solve_threaded_rope import rotate_inverse
from hangboard_packages.cord_paths import validate_cord_paths
base=Path(".context/placid-badger/nug-review/native-cord")
package=Path("Hangboards/frictitious-nug")
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=json.loads((base/"authoring-before-generation.json").read_text())
data=json.loads((package/"suspension.json").read_text())
permitted=copy.deepcopy(data)
for key,pose in permitted["suspension"]["canonicalPoses"].items():
 old=before["suspension"]["canonicalPoses"][key]
 pose["wrappedRoutes"]=old["wrappedRoutes"]
 pose["translation"][1]=old["translation"][1]
assert permitted==before,"Unexpected authored metadata change"
hashes=json.loads((base/"all-package-baseline-hashes.json").read_text())
current={str(p):sha(p) for p in sorted(Path("Hangboards").rglob("*")) if p.is_file()}
changes=[key for key in sorted(set(hashes)|set(current)) if hashes.get(key)!=current.get(key)]
assert changes==[str(package/"suspension.json")],changes
solid=json.loads(Path(".context/placid-badger/cad-raster-boards/frictitious-nug/solid-primary.json").read_text())
assert solid["sourceSHA256"]==sha(package/"frictitious-nug.FCStd")
mesh=trimesh.Trimesh(vertices=solid["vertices"],faces=solid["triangles"],process=False)
descriptor=json.loads((package/"assets/primary.model.json").read_text())
bounds=descriptor["modelBounds"]; anchor=(np.asarray(bounds["min"])+np.asarray(bounds["max"]))/2
anchor[1]=bounds["max"][1];anchor+=np.asarray(data["suspension"]["anchor"]["offsetFromBoardBounds"])
radii={x["id"]:x["radius"] for x in data["suspension"]["strands"]}
rests={x["id"]:x["restLength"] for x in data["suspension"]["strands"]}
report={"status":"passed","authoredMetadataUnchanged":True,"changedPackageFiles":changes,"sourceSHA256":solid["sourceSHA256"],"modelSHA256":sha(package/"assets/primary.usdz"),"descriptorSHA256":sha(package/"assets/primary.model.json"),"sidecarSHA256":sha(package/"suspension.json"),"solverSHA256":sha("Tools/HangboardCAD/native_cord_routes.py"),"poses":{}}
for key,pose in data["suspension"]["canonicalPoses"].items():
 support=rotate_inverse(pose["rotation"],anchor-np.asarray(pose["translation"]))
 paths={sid:np.vstack([support,route]) for sid,route in pose["wrappedRoutes"].items()}
 validate_cord_paths(paths,radii)
 detail={"height":pose["translation"][1],"wholeTubeGate":"passed","strands":{}}
 for sid,path in paths.items():
  native=data["ropeSolver"]["terminalsByStrandID"][sid]
  assert np.array_equal(path[-1],native["points"][0])
  entry=float((path[-2]-path[-1])@np.asarray([0,0,1 if sid.endswith("front") else -1]))
  assert entry>1e-8
  ratio=length(path)/rests[sid];assert ratio<=1+1e-6
  detail["strands"][sid]={"vertices":len(path),"certifiedClearance":checked_clearance(mesh,path,radii[sid]),"length":length(path),"lengthRatio":ratio,"outwardMouthEntryDot":entry,"actualMouthPreserved":True}
 report["poses"][key]=detail
(base/"post-apply-native-certificates.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
