from pathlib import Path
import json,hashlib,numpy as np
from pxr import Usd,UsdGeom
p=Path(__file__).resolve().parent;w=p.parent;a=w/'candidate/assets/primary.usdz';dp=w/'candidate/assets/primary.model.json';d=json.loads(dp.read_text());baseline=json.loads((p/'baseline.json').read_text());native=json.loads((p/'native-check-3ff3.json').read_text());stage=Usd.Stage.Open(str(a));bounds={};worlds={}
for prim in stage.Traverse():
 if not prim.IsA(UsdGeom.Mesh):continue
 m=UsdGeom.Mesh(prim);points=np.asarray(m.GetPointsAttr().Get(),dtype=float);mat=np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));q=(np.c_[points,np.ones(len(points))]@mat)[:,:3];worlds[prim.GetName()]=q;pn=q[:,[0,2,1]]*np.array([1000,-1000,1000]);bounds[prim.GetName()]=(pn.min(axis=0),pn.max(axis=0))
rows=[];errors=[]
for cid,expected in baseline['publishedDepthsMm'].items():
 ids=d['contacts'][cid]['nodeIDs'];lo=np.min([bounds[n][0] for n in ids],axis=0);hi=np.max([bounds[n][1] for n in ids],axis=0);actual=float(hi[1]-lo[1]);okay=abs(actual-expected)<.02;rows.append({'contactID':cid,'expectedDepthMM':expected,'actualMeshDepthMM':actual,'passesUnchanged002MMGate':okay})
 if not okay:errors.append(cid+' actual published support depth')
whole=np.concatenate(list(worlds.values()));lo=whole.min(axis=0);hi=whole.max(axis=0);boundrows=[]
for cid,c in d['contacts'].items():
 q=np.concatenate([worlds[n] for n in c['nodeIDs']]);flat=np.c_[(q[:,0]-lo[0])/(hi[0]-lo[0]),(q[:,1]-lo[1])/(hi[1]-lo[1])];want=c['facePlaneAABB'];error=float(max(np.max(np.abs(flat.min(axis=0)-want['min'])),np.max(np.abs(flat.max(axis=0)-want['max']))));boundrows.append({'contactID':cid,'maximumNormalizedBoundsError':error})
 if error>5e-9:errors.append(cid+' descriptor normalized bounds mismatch')
face=[float((hi[0]-lo[0])*1000),float((hi[1]-lo[1])*1000)]
if abs(face[0]-711)>.02 or abs(face[1]-222)>.02:errors.append('actual face envelope')
r={'status':'pass' if not errors else 'fail','blockingFindings':errors,'sourceSHA256':native['sourceSHA256'],'modelSHA256':hashlib.sha256(a.read_bytes()).hexdigest(),'descriptorSHA256':hashlib.sha256(dp.read_bytes()).hexdigest(),'faceEnvelopeMM':face,'publishedDepths':rows,'descriptorContactBounds':boundrows,'toleranceMM':.02};(p/'export-facts-3ff3-v2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'blockingFindings':errors,'maxDepthErrorMM':max(abs(x['expectedDepthMM']-x['actualMeshDepthMM']) for x in rows),'maximumNormalizedBoundsError':max(x['maximumNormalizedBoundsError'] for x in boundrows)},indent=2))
