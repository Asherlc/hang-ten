import FreeCAD as A,json,hashlib,zipfile
from pathlib import Path
w=Path(__file__).resolve().parent;source=w/'candidate/metolius-simulator-3d.FCStd'
expected='40e42ed072a72946d11756cd6f92047fd0d5acd79eb33946cb2188441babbbde';assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
original=A.openDocument(str(source));manifest=original.HangTenBoardManifest
assert original.HangTenSurfaceNormals and abs(original.HangTenTessellationDeflection-.28)<1e-10
assert 'HangTenUVNodeSurfaceNormals' not in original.PropertiesList
original.addProperty('App::PropertyBool','HangTenUVNodeSurfaceNormals','HangTen','Use native tessellation UV nodes for analytic normals; exact legacy fallback for ambiguous triangles')
original.HangTenUVNodeSurfaceNormals=True;original.recompute()
bad=[(o.Name,list(o.State)) for o in original.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}];assert not bad,bad
assert original.HangTenBoardManifest==manifest
folder=w/'uv-candidate';folder.mkdir(exist_ok=True);(folder/'assets').mkdir(exist_ok=True);out=folder/'metolius-simulator-3d.FCStd';original.saveAs(str(out));A.closeDocument(original.Name)
reopened=A.openDocument(str(out));reopened.recompute();assert reopened.HangTenBoardManifest==manifest and reopened.HangTenUVNodeSurfaceNormals
bad=[(o.Name,list(o.State)) for o in reopened.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}];assert not bad,bad
with zipfile.ZipFile(source) as a,zipfile.ZipFile(out) as b:
 names=[n for n in a.namelist() if n.lower().endswith(('.brp','.brep'))]
 assert names and all(a.read(n)==b.read(n) for n in names)
 geometry={n:hashlib.sha256(a.read(n)).hexdigest() for n in names}
report={'status':'pass','beforeSourceSHA256':expected,'sourceSHA256':hashlib.sha256(out.read_bytes()).hexdigest(),'enabledProperty':'HangTenUVNodeSurfaceNormals','analyticSurfaceNormals':True,'tessellationDeflectionMM':.28,'rawManifestExact':True,'allBrepEntriesByteIdentical':True,'brepEntryCount':len(geometry),'brepEntrySHA256':geometry,'sourcePath':str(out),'reopenRecomputeClean':True,'geometryChanged':False}
(w/'uv-source-preservation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='brepEntrySHA256'},indent=2));A.closeDocument(reopened.Name)
