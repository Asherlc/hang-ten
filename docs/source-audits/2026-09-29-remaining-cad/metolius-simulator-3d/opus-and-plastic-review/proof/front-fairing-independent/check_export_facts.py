from pathlib import Path
import sys,json,hashlib,numpy as np
from pxr import Usd,UsdGeom
p=Path(__file__).resolve().parent;w=p.parent;source=Path(sys.argv[1]);a=Path(sys.argv[2]);dp=Path(sys.argv[3]);native_report=Path(sys.argv[4]);out=Path(sys.argv[5]);d=json.loads(dp.read_text());baseline=json.loads((p/'baseline.json').read_text());native=json.loads(native_report.read_text());assert native['sourceSHA256']==hashlib.sha256(source.read_bytes()).hexdigest()=='b7223032abe4b5c00a8b16d8ddcafed8b836d806795f1d37bbffab80ce5560ef';stage=Usd.Stage.Open(str(a));bounds={};worlds={}
for prim in stage.Traverse():
 if not prim.IsA(UsdGeom.Mesh):continue
 m=UsdGeom.Mesh(prim);points=np.asarray(m.GetPointsAttr().Get(),dtype=float);mat=np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));q=(np.c_[points,np.ones(len(points))]@mat)[:,:3];worlds[prim.GetName()]=q;pn=q[:,[0,2,1]]*np.array([1000,-1000,1000]);bounds[prim.GetName()]=(pn.min(axis=0),pn.max(axis=0))
rows=[];errors=[]
for cid,expected in baseline['publishedDepthsMm'].items():
 ids=d['contacts'][cid]['nodeIDs'];lo=np.min([bounds[n][0] for n in ids],axis=0);hi=np.max([bounds[n][1] for n in ids],axis=0);actual=float(hi[1]-lo[1]);okay=abs(actual-expected)<.001;rows.append({'contactID':cid,'expectedDepthMM':expected,'actualMeshDepthMM':actual,'passes0001MMGate':okay})
 if not okay:errors.append(cid+' actual published support depth')
whole=np.concatenate(list(worlds.values()));lo=whole.min(axis=0);hi=whole.max(axis=0);boundrows=[]
for cid,c in d['contacts'].items():
 q=np.concatenate([worlds[n] for n in c['nodeIDs']]);flat=np.c_[(q[:,0]-lo[0])/(hi[0]-lo[0]),(q[:,1]-lo[1])/(hi[1]-lo[1])];want=c['facePlaneAABB'];error=float(max(np.max(np.abs(flat.min(axis=0)-want['min'])),np.max(np.abs(flat.max(axis=0)-want['max']))));boundrows.append({'contactID':cid,'maximumNormalizedBoundsError':error})
 if error>5e-9:errors.append(cid+' descriptor normalized bounds mismatch')
face=[float((hi[0]-lo[0])*1000),float((hi[1]-lo[1])*1000)]
if abs(face[0]-711)>.001 or abs(face[1]-222)>.001:errors.append('actual face envelope')
if abs(hi[0]+lo[0])*1000>.001:errors.append('global left/right symmetric mesh bounds')
if max(abs(lo[i]-d['modelBounds']['min'][i]) for i in range(3))>1e-9 or max(abs(hi[i]-d['modelBounds']['max'][i]) for i in range(3))>1e-9:errors.append('descriptor model bounds mismatch')
r={'status':'pass' if not errors else 'fail','blockingFindings':errors,'sourceSHA256':native['sourceSHA256'],'modelSHA256':hashlib.sha256(a.read_bytes()).hexdigest(),'descriptorSHA256':hashlib.sha256(dp.read_bytes()).hexdigest(),'faceEnvelopeMM':face,'publishedDepths':rows,'descriptorContactBounds':boundrows,'toleranceMM':.001,'wholeRuntimeBoundsM':{'min':lo.tolist(),'max':hi.tolist()},'symmetricXBoundsErrorMM':float(abs(hi[0]+lo[0])*1000)};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'blockingFindings':errors,'maxDepthErrorMM':max(abs(x['expectedDepthMM']-x['actualMeshDepthMM']) for x in rows),'maximumNormalizedBoundsError':max(x['maximumNormalizedBoundsError'] for x in boundrows)},indent=2))
