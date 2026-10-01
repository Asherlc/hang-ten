import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path("Tools/HangboardCAD").resolve()))
import FreeCAD as A
import compile_board as c
from contact_model_descriptor import NodeBinding,compile_descriptor
base=Path(".context/placid-badger/nug-pinch-review/python-contract")
p=Path(".context/placid-badger/nug-review/native-cord/HEAD-package/frictitious-nug.FCStd")
sha=hashlib.sha256(p.read_bytes()).hexdigest();d=A.openDocument(str(p.resolve()))
body=d.getObject("RightBackEntryCut");shape_before=body.Shape.exportBrepToString()
top=d.getObject("jug_40");bottom=d.getObject("pinch_60")
top.addProperty("App::PropertyStringList","AdditionalContactIDs","HangTen");top.AdditionalContactIDs=["pinch-60"]
bottom.addProperty("App::PropertyString","HangTenDepthAxis","HangTen");bottom.HangTenDepthAxis="z"
objects=c._bound_objects(d,"primary");specs=[c._node_specification(obj,1) for obj in objects]
board=c.cad_source.load_board(p);c.contract.validate_bindings(specs,board,1,[])
depths=c._validate_published_depths([o for o in objects if o.NodeRole=="contact"],c._declared_depths(board,1,"primary"),1,.05,{"x":130,"y":40,"z":60})
assert depths["pinch-60"]==60 and depths["jug-40"]==40
asset=Path("Hangboards/frictitious-nug/assets/primary.usdz");old=c.usdz_writer.read_usdz(asset)
result=compile_descriptor(asset.read_bytes(),[NodeBinding(s["id"],s["role"],s.get("contact"),tuple(s.get("additionalContactIDs",[]))) for s in specs],{name:node["points_m"] for name,node in old["nodes"].items()},frozenset(x["id"] for x in board["contacts"]))
assert result.contacts["pinch-60"].node_ids==("nug_jug_40","nug_pinch_60")
assert len(result.nodes)==7 and len(old["nodes"])==7
assert body.Shape.exportBrepToString()==shape_before
A.closeDocument(d.Name);assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
report={"status":"passed","sourceSnapshotSHA256":sha,"readOnlyInMemoryMetadataOnly":True,"savedSource":False,"bodyBrepUnchanged":True,"singleExportNodeInventory":len(old["nodes"]),"depthsMM":depths,"pinchNodes":list(result.contacts["pinch-60"].node_ids),"jugNodes":list(result.contacts["jug-40"].node_ids),"pinchBounds":result.to_json()["contacts"]["pinch-60"]["facePlaneAABB"],"nativeAdditionalPropertyType": "App::PropertyStringList"}
(base/"native-in-memory-smoke.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
