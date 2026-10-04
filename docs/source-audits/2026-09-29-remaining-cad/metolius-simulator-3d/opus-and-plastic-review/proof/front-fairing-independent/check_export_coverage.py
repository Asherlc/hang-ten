import sys,json,hashlib,time
from pathlib import Path
import numpy as np,trimesh
from pxr import Usd,UsdGeom
asset=Path(sys.argv[1]);native_path=Path(sys.argv[2]);proof_path=Path(sys.argv[3]);out=Path(sys.argv[4]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof=json.loads(proof_path.read_text());assert sha(native_path)==proof['nativeBodyMeshSHA256'];assert proof['sourceSHA256']=='b7223032abe4b5c00a8b16d8ddcafed8b836d806795f1d37bbffab80ce5560ef';native=json.loads(native_path.read_text());nm=trimesh.Trimesh(vertices=native['p'],faces=native['t'],process=False);points=[];faces=[];offset=0
stage=Usd.Stage.Open(str(asset))
for prim in stage.Traverse():
 if not prim.IsA(UsdGeom.Mesh):continue
 m=UsdGeom.Mesh(prim);p=np.asarray(m.GetPointsAttr().Get(),dtype=float);mat=np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));world=(np.c_[p,np.ones(len(p))]@mat)[:,:3];pn=world[:,[0,2,1]]*np.array([1000,-1000,1000]);idx=np.asarray(m.GetFaceVertexIndicesAttr().Get(),dtype=int).reshape(-1,3);points.append(pn);faces.append(idx+offset);offset+=len(pn)
em=trimesh.Trimesh(vertices=np.concatenate(points),faces=np.concatenate(faces),process=False)
def measure(query,target,label):
 worst=[];distances=[]
 for start in range(0,len(query),512):
  q=query[start:start+512];nearest,distance,tri=trimesh.proximity.closest_point(target,q);distances.extend(distance.tolist());order=np.argsort(distance)[-5:];worst.extend({'distanceMM':float(distance[i]),'sampleIndex':start+int(i),'pointMM':q[i].tolist(),'nearestPointMM':nearest[i].tolist(),'targetTriangle':int(tri[i])} for i in order);worst=sorted(worst,key=lambda x:x['distanceMM'],reverse=True)[:20]
 d=np.array(distances);print(label,'complete',len(d),'max',d.max(),flush=True);return {'sampleCount':len(d),'maximumDistanceMM':float(d.max()),'p99DistanceMM':float(np.quantile(d,.99)),'above028MM':int(np.count_nonzero(d>.28)),'worstSamples':worst}
r={'sourceSHA256':proof['sourceSHA256'],'modelSHA256':sha(asset),'nativeBodyMeshSHA256':sha(native_path),'provenanceSHA256':sha(proof_path),'nativeVerticesToExport':measure(nm.vertices,em,'native vertices'),'nativeTriangleCentersToExport':measure(nm.triangles_center,em,'native triangle centers'),'exportTriangleCentersToNative':measure(em.triangles_center,nm,'export triangle centers'),'limits':['Finite full-mesh vertex/triangle-center coverage at the unchanged.28mm tessellation setting. This is not a continuous Hausdorff proof or exact native-surface clearance certificate.','Distances compare two tessellations; no sourced-depth/envelope/contact tolerance is changed. Large witnesses require specific geometric review.','Export topology and app appearance are separate gates.']};r['status']='pass' if all(r[k]['above028MM']==0 for k in ['nativeVerticesToExport','nativeTriangleCentersToExport','exportTriangleCentersToNative']) else 'requires-review';out.write_text(json.dumps(r,indent=2)+'\n');print('Report',out,flush=True)
