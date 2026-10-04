import copy,hashlib,json,sys
from pathlib import Path
import numpy as np,trimesh
sys.path.insert(0,"Tools/HangboardCAD")
from native_cord_routes import checked_clearance,length
from solve_threaded_rope import rotate_inverse
from hangboard_packages.cord_paths import validate_cord_paths
base=Path(".context/placid-badger/nug-pinch-review/native-cord")
package=Path("Hangboards/frictitious-nug")
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
data=json.loads((package/"suspension.json").read_text())
assert sha(package/"suspension.json")=="8a3fdf291c1ef34588425a4a7a73524fab33abdbb5a561456d571ecdd86642fc"
proof=json.loads(Path(".context/placid-badger/nug-pinch-review/package-change-proof.json").read_text())
changes=proof["changedPackageFiles"]
solid=json.loads((base/"solid-primary.json").read_text())
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
