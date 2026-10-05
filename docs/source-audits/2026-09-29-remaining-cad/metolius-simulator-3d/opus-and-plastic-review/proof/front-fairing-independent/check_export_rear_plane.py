import sys,json,hashlib
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
asset,native_path,proof_path,out=map(Path,sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads(proof_path.read_text());assert proof["nativeBodyMeshSHA256"]==sha(native_path)
stage=Usd.Stage.Open(str(asset));rows=[];polygons=[];all_plane_vertices=0
for prim in stage.Traverse():
 if not prim.IsA(UsdGeom.Mesh):continue
 m=UsdGeom.Mesh(prim);p=np.asarray(m.GetPointsAttr().Get(),float);n=np.asarray(m.GetNormalsAttr().Get(),float);ix=np.asarray(m.GetFaceVertexIndicesAttr().Get(),int).reshape(-1,3);mat=np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));world=(np.c_[p,np.ones(len(p))]@mat)[:,:3];wn=n@np.linalg.inv(mat[:3,:3]).T;wn/=np.linalg.norm(wn,axis=1)[:,None]
 plane=np.abs(world[:,2])<1e-8;all_plane_vertices+=int(plane.sum());ids=np.flatnonzero(plane[ix].all(axis=1));tri=world[ix[ids]];norm=wn[ix[ids]];flat=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(flat,axis=1);valid=length>1e-20;cosine=-norm[:,:,2];bad=np.any(cosine<1-1e-6,axis=1);opposed=np.any(cosine<0,axis=1);flatz=flat[valid,2]/length[valid]
 for t in tri:polygons.append(Polygon(t[:,:2]*1000))
 details=[]
 for k in np.flatnonzero(bad):details.append({"triangle":int(ids[k]),"areaMM2":float(length[k]*5e5),"runtimeVerticesM":tri[k].tolist(),"nativeCenterMM":[float(tri[k,:,0].mean()*1000),float(-tri[k,:,2].mean()*1000),float(tri[k,:,1].mean()*1000)],"wallNormalCosines":cosine[k].tolist(),"geometricNormalWallCosine":float(-flat[k,2]/length[k]) if length[k] else None})
 if len(ids):rows.append({"node":prim.GetName(),"rearTriangles":len(ids),"rearTriangleAreaMM2":float(length.sum()*5e5),"rearNormalMinimumWallCosine":float(cosine.min()),"nonWallNormalTriangleCount":int(bad.sum()),"opposedNormalTriangleCount":int(opposed.sum()),"opposedNormalTriangleAreaMM2":float(length[opposed].sum()*5e5),"geometricNormalsAllWallFacing":bool(np.all(flatz< -1+1e-6)),"largestNonWallNormalTriangles":sorted(details,key=lambda x:x['areaMM2'],reverse=True)[:30]})
native=json.loads(native_path.read_text());np_=np.array(native['p']);nt=np.array(native['t']);rear=np.abs(np_[:,1])<1e-5;native_tri=np_[nt[rear[nt].all(axis=1)]];reference=unary_union([Polygon(t[:,[0,2]]) for t in native_tri]);export=unary_union(polygons);missing=reference.difference(export);extra=export.difference(reference);lower=box(-50,0,50,60)
report={"status":"pass" if all(r['opposedNormalTriangleCount']==0 and r['geometricNormalsAllWallFacing'] for r in rows) and missing.area<.01 else "requires-review","sourceSHA256":proof['sourceSHA256'],"modelSHA256":sha(asset),"nativeBodyMeshSHA256":sha(native_path),"coordinateBasis":"Verified writer native millimetres (X,Y,Z) -> runtime metres (X,Z,-Y)/1000; native rear Y=0,+Y outward maps runtime rear Z=0,-Z outward.","planeToleranceM":1e-8,"allStoredVerticesOnRearPlane":all_plane_vertices,"nativeRearTriangleCount":len(native_tri),"exportRearTriangleCount":sum(r['rearTriangles'] for r in rows),"nativeRearAreaMM2":reference.area,"exportRearUnionAreaMM2":export.area,"missingRearAreaMM2":missing.area,"extraRearAreaMM2":extra.area,"lowerCenterWatchWindowNativeMM":{"x":[-50,50],"z":[0,60]},"lowerCenterMissingRearAreaMM2":missing.intersection(lower).area,"rows":rows,"limits":["All rear-plane facets and their authored corner normals inspected; normal checks exclude non-rear side facets which legitimately share rear edge positions.","Planar triangle union is compared to pinned native body tessellation; this is not an assertion of exact welded topology elsewhere.","Actual app rear view remains the appearance authority; CPU preview shading is not used as geometry evidence."]}
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
