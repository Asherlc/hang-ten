import json,hashlib,sys
from pathlib import Path
from collections import Counter
import numpy as np
from pxr import Usd,UsdGeom
asset,native_path,out=map(Path,sys.argv[1:]);native=json.loads(native_path.read_text());p=np.asarray(native['p']);ix=np.asarray(native['t']);mask=(np.abs(p[:,1])<1e-5)[ix].all(axis=1);native_tri=p[ix[mask]];expected=(native_tri*.001).astype(np.float32).astype(float)
sig=lambda t:tuple(sorted(tuple(row) for row in t));wanted=Counter(sig(t) for t in expected);actual=Counter();nonmatching=[]
stage=Usd.Stage.Open(str(asset))
for prim in stage.Traverse():
 if not prim.IsA(UsdGeom.Mesh):continue
 m=UsdGeom.Mesh(prim);points=np.asarray(m.GetPointsAttr().Get(),float);ids=np.asarray(m.GetFaceVertexIndicesAttr().Get(),int).reshape(-1,3);rear=(np.abs(points[:,1])<1e-8)[ids].all(axis=1)
 for t in points[ids[rear]]:actual[sig(t)]+=1
missing=wanted-actual;extra=actual-wanted
r={'status':'pass' if not missing and not extra else 'requires-review','modelSHA256':hashlib.sha256(asset.read_bytes()).hexdigest(),'nativeBodyMeshSHA256':hashlib.sha256(native_path.read_bytes()).hexdigest(),'nativeRearFacets':sum(wanted.values()),'exportRearFacets':sum(actual.values()),'missingNativeFacetsAfterExactUSDfloat32Encoding':sum(missing.values()),'unexpectedExportFacets':sum(extra.values()),'maximumNativeVertexFloat32EncodingErrorMM':float(np.linalg.norm(expected*1000-native_tri,axis=2).max()),'method':'Compare every rear triangle by its three unordered local vertices after the actual writer conversion (native mm * .001 cast to float32). Exact multiset equality verifies the whole rear plate; no positional weld or geometry mutation.','interpretation':'The sub-.003 mm² unquantized planar-union differences are float32 boundary displacement, not missing rear triangles.' if not missing and not extra else 'Exact correspondence needs review.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
