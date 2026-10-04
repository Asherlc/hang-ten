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

data=load(asset);native=json.loads((h/'shape-feedback.json').read_text());rows=[];fail=[]
for section in native['roundFlatRoofSections']:
 y=section['yMM'];vals=[];errors=[]
 for x,z in zip(section['xMM'],section['zMM']):
  hit=roof(data,x,y);vals.append(hit['zMM'] if hit else None)
  if hit and z is not None:errors.append(abs(hit['zMM']-z))
  elif hit is None and z is not None:fail.append('missing exported roof '+str((x,y)))
 minima=[]
 for i in range(1,len(vals)-1):
  if None not in vals[i-1:i+2] and vals[i]<min(vals[i-1],vals[i+1])-.0001:minima.append({'xMM':section['xMM'][i],'dropMM':min(vals[i-1],vals[i+1])-vals[i]})
 if y in [-.01,-10] and minima:fail.append('localized exported rear roof dip '+str(y))
 if max(errors,default=0)>.28:fail.append('roof native/mesh error exceeds deflection '+str(y))
 rows.append({'yMM':y,'xMM':section['xMM'],'zMM':vals,'maxNativeDeviationMM':max(errors,default=0),'sampledLocalMinima':minima})
def x_intersections(y,z):
 t,n,lo,hi=data;mask=(lo[:,1]<=y+1e-8)&(hi[:,1]>=y-1e-8)&(lo[:,2]<=z+1e-8)&(hi[:,2]>=z-1e-8);t=t[mask]
 e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];d=np.array([1,0,0.]);hv=np.cross(d,e2);a=np.einsum('ij,ij->i',e1,hv);ok=np.abs(a)>1e-10;f=np.zeros_like(a);f[ok]=1/a[ok];ss=np.array([0,y,z])-t[:,0];u=f*np.einsum('ij,ij->i',ss,hv);q=np.cross(ss,e1);v=f*(q@d);x=f*np.einsum('ij,ij->i',e2,q);ok&=(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(np.abs(x)<70)
 values=sorted(x[ok]);out=[]
 for x in values:
  if not out or abs(x-out[-1])>1e-5:out.append(float(x))
 return out
widths=[]
for row in native['domeWidths']:
 expected=row['candidateIntersectionsXMM']
 if not expected or not all(abs(x)<46.49 for x in expected):continue
 values=x_intersections(row['yMM'],row['zMM']);error=max((abs(x-y) for x,y in zip(values,expected)),default=0) if len(values)==len(expected) else None
 if error is None or error>.28:fail.append('export dome section '+str((row['yMM'],row['zMM'])))
 widths.append({'yMM':row['yMM'],'zMM':row['zMM'],'nativeXMM':expected,'meshXMM':values,'maxDifferenceMM':error})
r={'status':'pass' if not fail else 'fail','blockingFindings':fail,'modelSHA256':sha(asset),'nativeSourceSHA256':native['sourceSHA256'],'nativeReportSHA256':sha(h/'shape-feedback.json'),'roofSections':rows,'domeWidths':widths,'maxRoofNativeDeviationMM':max(r['maxNativeDeviationMM'] for r in rows),'limits':'Finite actualmesh sections; no globalsmoothness or manufacturerexact geometry claim. Chord mesh geometry and native spline section differences bounded at tested stations.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['roofSections','domeWidths']},indent=2));raise SystemExit(bool(fail))
