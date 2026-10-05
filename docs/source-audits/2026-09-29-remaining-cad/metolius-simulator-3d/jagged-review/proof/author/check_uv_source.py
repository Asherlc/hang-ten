import FreeCAD as A,json,hashlib
from pathlib import Path
w=Path(__file__).resolve().parent;a=A.openDocument(str(w/'validated-geometry-40e42/metolius-simulator-3d.FCStd'));b=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));a.recompute();b.recompute();assert a.HangTenBoardManifest==b.HangTenBoardManifest;assert b.HangTenUVNodeSurfaceNormals and b.HangTenSurfaceNormals
for d in [a,b]:
 bad=[(o.Name,list(o.State)) for o in d.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}];assert not bad,bad
 assert d.BodySolid.Shape.isValid() and len(d.BodySolid.Shape.Solids)==1
 assert len([o for o in d.Objects if getattr(o,'NodeRole','')=='contact'])==30
assert a.BodySolid.Shape.Volume==b.BodySolid.Shape.Volume and a.BodySolid.Shape.Area==b.BodySolid.Shape.Area
p=w/'uv-source-preservation.json';r=json.loads(p.read_text());r.update({'status':'pass','rawManifestExact':True,'reopenRecomputeClean':True,'bodyVolumeAndAreaExact':True,'sourceSHA256':hashlib.sha256((w/'candidate/metolius-simulator-3d.FCStd').read_bytes()).hexdigest()});p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
