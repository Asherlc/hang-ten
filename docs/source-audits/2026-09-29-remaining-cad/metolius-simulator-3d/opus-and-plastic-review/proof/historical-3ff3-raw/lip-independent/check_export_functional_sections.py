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

native_path=Path(sys.argv[4]);local_path=Path(sys.argv[5]);native=json.loads(native_path.read_text());local=json.loads(local_path.read_text());assert native['sourceSHA256']==local['sourceSHA256'];descriptor=json.loads(Path(sys.argv[3]).read_text());data=load(asset);stage=Usd.Stage.Open(str(asset));node_data={}
for prim in stage.Traverse():
 if not prim.IsA(UsdGeom.Mesh):continue
 m=UsdGeom.Mesh(prim);pts=np.asarray(m.GetPointsAttr().Get(),dtype=float);mat=np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));world=(np.c_[pts,np.ones(len(pts))]@mat)[:,:3];nativepts=world[:,[0,2,1]]*np.array([1000,-1000,1000]);idx=np.asarray(m.GetFaceVertexIndicesAttr().Get(),dtype=int).reshape(-1,3);tri=nativepts[idx];dummy_normals=np.zeros_like(tri);dummy_normals[:,:,2]=1;node_data[prim.GetName()]=(tri,dummy_normals,tri.min(axis=1),tri.max(axis=1))
def contactdata(cid):
 parts=[node_data[n] for n in descriptor['contacts'][cid]['nodeIDs']];return tuple(np.concatenate([x[i] for x in parts]) for i in range(4))
# roof() normals are irrelevant in this geometry-only membership check.
rows=[];fail=[]
for section in native['slopers']:
 cid=section['id'];x=section['xMM'];mesh=contactdata(cid);lo=mesh[0].min(axis=(0,1));hi=mesh[0].max(axis=(0,1));samples=[]
 for probe in section['roofSamples']:
  y=probe['yMM'];allhit=roof(data,x,y);hit=roof(mesh,x,y);error=abs(hit['zMM']-probe['roofZMM']) if hit else None;gap=abs(hit['zMM']-allhit['zMM']) if hit and allhit else None
  if error is None or error>.28 or gap is None or gap>.002:fail.append('sloper exported roof/contact '+str((cid,x,y)))
  samples.append({'yMM':y,'nativeToContactMeshZErrorMM':error,'bodyRoofToContactMeshZGapMM':gap})
 if abs(lo[1]+94)>.28 or abs((hi[1]-lo[1])-section['expectedDepthMM'])>.28:fail.append('frontanchored exported contact bounds '+cid)
 rows.append({'id':cid,'xMM':x,'meshYBoundsMM':[float(lo[1]),float(hi[1])],'samples':samples})
jugmesh=contactdata('jug-14-center');jugs=[]
for section in native['centerJug']:
 x=section['xMM'];probes=[]
 for point in section['contactSamples']:
  y=point['yMM'];a=roof(data,x,y);b=roof(jugmesh,x,y);error=abs(b['zMM']-point['zMM']) if b else None;gap=abs(a['zMM']-b['zMM']) if a and b else None
  if error is None or error>.28 or gap is None or gap>.002:fail.append('jug exported curved contact '+str((x,y)))
  probes.append({'yMM':y,'nativeToContactMeshZErrorMM':error,'bodyRoofToContactMeshZGapMM':gap})
 points=[(y,roof(data,x,y)) for y in section['yMM']];points=[(y,z['zMM']) for y,z in points if z];cy,cz=max(points,key=lambda a:a[1]);rear=roof(data,x,-.01);front=roof(data,x,-93.9)
 if not (60<=-cy<=75 and rear and front and cz-rear['zMM']>5 and cz-front['zMM']>5):fail.append('jug exported crest/returns '+str(x))
 jugs.append({'xMM':x,'crestYMM':cy,'crestZMM':cz,'rearRoofZMM':rear['zMM'] if rear else None,'frontRoofZMM':front['zMM'] if front else None,'contactSamples':probes})
# Exact logical X47 membership and lower curved nose coverage on exported triangles.
roundmesh=contactdata('round-sloper-3-center');membership=[]
for point in local['rootMembership']:
 x,y=point['xMM'],point['yMM'];target=jugmesh if point['expected']=='jug' else roundmesh;other=roundmesh if point['expected']=='jug' else jugmesh
 hit=roof(target,x,y);unexpected=roof(other,x,y);error=abs(hit['zMM']-point['zMM']) if hit else None
 if error is None or error>.28 or unexpected is not None:fail.append('exported X47 assignment '+str((x,y)))
 membership.append({'xMM':x,'yMM':y,'expected':point['expected'],'nativeZErrorMM':error,'unexpectedOtherContactIntersection':unexpected})
roll=[]
for point in local['jugForwardRollMembership']:
 x,y=point['xMM'],point['yMM'];hit=roof(jugmesh,x,y);error=abs(hit['zMM']-point['zMM']) if hit else None
 if error is None or error>.28:fail.append('exported curved upper roll '+str((x,y)))
 roll.append({'xMM':x,'yMM':y,'nativeZErrorMM':error})
r={'status':'pass' if not fail else 'fail','blockingFindings':fail,'modelSHA256':sha(asset),'descriptorSHA256':sha(Path(sys.argv[3])),'nativeSourceSHA256':native['sourceSHA256'],'nativeReportSHA256':sha(native_path),'localNativeReportSHA256':sha(local_path),'rootMembership':membership,'jugForwardRoll':roll,'slopers':rows,'centerJug':jugs,'limits':'Finite actualtriangle native-frame probes; operator display-intent position/return thresholds are not maker or ergonomic facts. Whole-image Opus and user acceptance remain separate.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['slopers','centerJug']},indent=2));raise SystemExit(bool(fail))
