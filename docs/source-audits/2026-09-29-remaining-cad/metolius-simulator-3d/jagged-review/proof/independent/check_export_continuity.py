import sys,json,hashlib,math
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom
h=Path(__file__).resolve().parent;asset=Path(sys.argv[1]);out=Path(sys.argv[2]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 stage=Usd.Stage.Open(str(path));triangles=[];normals=[]
 for prim in stage.Traverse():
  if not prim.IsA(UsdGeom.Mesh):continue
  m=UsdGeom.Mesh(prim);p=np.asarray(m.GetPointsAttr().Get(),dtype=float);n=np.asarray(m.GetNormalsAttr().Get(),dtype=float)
  mat=np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));world=(np.c_[p,np.ones(len(p))]@mat)[:,:3]
  native=world[:,[0,2,1]]*np.array([1000,-1000,1000]);worldn=n@np.linalg.inv(mat[:3,:3]).T;nativen=worldn[:,[0,2,1]]*np.array([1,-1,1]);nativen/=np.linalg.norm(nativen,axis=1)[:,None]
  idx=np.array(m.GetFaceVertexIndicesAttr().Get()).reshape(-1,3);triangles.append(native[idx]);normals.append(nativen[idx])
 t=np.concatenate(triangles);n=np.concatenate(normals);return t,n,t.min(axis=1),t.max(axis=1)
def roof(data,x,y):
 t,n,lo,hi=data;mask=(lo[:,0]<=x+1e-8)&(hi[:,0]>=x-1e-8)&(lo[:,1]<=y+1e-8)&(hi[:,1]>=y-1e-8);t=t[mask];n=n[mask]
 e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];d=np.array([0,0,1.]);hv=np.cross(d,e2);a=np.einsum('ij,ij->i',e1,hv);okay=np.abs(a)>1e-10;f=np.zeros_like(a);f[okay]=1/a[okay];s=np.array([x,y,0])-t[:,0];u=f*np.einsum('ij,ij->i',s,hv);q=np.cross(s,e1);v=f*(q@d);z=f*np.einsum('ij,ij->i',e2,q);okay&=(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)
 ids=np.flatnonzero(okay)
 if not len(ids):return None
 i=ids[np.argmax(z[ids])];normal=(1-u[i]-v[i])*n[i,0]+u[i]*n[i,1]+v[i]*n[i,2];normal/=np.linalg.norm(normal)
 return {'zMM':float(z[i]),'normal':normal.tolist()}
def angle(a,b):return math.degrees(math.acos(float(np.clip(np.dot(a,b),-1,1))))
new=load(asset);old=load(h/'before-primary.usdz');native=json.loads((h/'continuity-check.json').read_text());rows=[];fail=[]
for r in native['roofSections']:
 x,y=r['xMM'],r['yMM'];probes=[]
 for p in r['probes']:
  eps=p['epsilonMM'];left=roof(new,x-eps,y);right=roof(new,x+eps,y)
  if not left or not right:fail.append(f'roof mesh missing {x}/{y}');continue
  if not p['left'] or not p['right']:
   fail.append(f'native grazing probe absent {x}/{y}, epsilon{eps}; retained for explicit disposition');continue
  error=max(abs(left['zMM']-p['left']['zMM']),abs(right['zMM']-p['right']['zMM']))
  if error>.28:fail.append(f'native/mesh deviation {x}/{y}: {error}')
  probes.append({'epsilonMM':eps,'left':left,'right':right,'signedHeightDifferenceMM':right['zMM']-left['zMM'],'interpolatedNormalAngleDegrees':angle(left['normal'],right['normal']),'maxNativeDeviationMM':error})
 if len(probes)==2:
  limit=(.01*probes[1]['signedHeightDifferenceMM']-.001*probes[0]['signedHeightDifferenceMM'])/.009
  if abs(limit)>.005:fail.append(f'finite exported roof step {x}/{y}: {limit}')
  before=[]
  if x in [47,148,258]:
   for eps in [.01,.001]:
    l=roof(old,x-eps,y);rr=roof(old,x+eps,y);before.append({'epsilonMM':eps,'heightDifferenceMM':abs(rr['zMM']-l['zMM']) if l and rr else None})
  rows.append({'xMM':x,'yMM':y,'probes':probes,'extrapolatedSignedStepMM':limit,'priorSeam':before})
r={'status':'fail' if fail else 'pass','blockingFindings':fail,'modelSHA256':sha(asset),'nativeSourceSHA256':native['sourceSHA256'],'nativeCheckSHA256':sha(h/'continuity-check.json'),'sections':rows,'maxNativeDeviationMM':max(p['maxNativeDeviationMM'] for r in rows for p in r['probes']),'maxExtrapolatedStepMM':max(abs(r['extrapolatedSignedStepMM']) for r in rows),'limits':'Local vertical ray/triangle sections compare actual exported geometry with native solid and prior asset; interpolated authored vertex normals quantify local shading continuity. No global C1/C2 or physical surface certification.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='sections'},indent=2));raise SystemExit(bool(fail))
