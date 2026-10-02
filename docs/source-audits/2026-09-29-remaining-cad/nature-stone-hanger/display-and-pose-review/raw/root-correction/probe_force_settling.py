from pathlib import Path
import json,sys,hashlib,numpy as np,trimesh
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'))
from native_cord_guides import certify_active_reactions,certify_groove_traversal,certify_bore_entry
from native_cord_routes import checked_clearance
s=json.loads((w/'native-collision-vertical.json').read_text());m=trimesh.Trimesh(s['vertices'],s['triangles'],process=False)
r=json.loads((w/'planar-right-force-diagnosis.json').read_text())['leads']['Right'];p=np.array(r['path']);failure=r['failureReport'];steps=[]
for iteration in range(5):
 n=len(p)-2;J=np.zeros((3*n,3*n))
 for k,v in enumerate(np.diff(p,axis=0)):
  length=np.linalg.norm(v);d=v/length;K=(np.eye(3)-np.outer(d,d))/length
  for a,sa in ((k,-1),(k+1,1)):
   if not 0<a<len(p)-1:continue
   for b,sb in ((k,-1),(k+1,1)):
    if 0<b<len(p)-1:J[3*(a-1):3*a,3*(b-1):3*b]+=sa*sb*K
 residual=np.array(failure['nodalResiduals']).ravel();step=np.linalg.lstsq(J,-residual,rcond=1e-10)[0].reshape(-1,3);maximum=float(np.linalg.norm(step,axis=1).max());assert maximum<1e-5,maximum
 q=p.copy();q[1:-1]+=step;record={'iteration':iteration,'maxStepM':maximum,'path':q.tolist()}
 try:
  record['clearance']=checked_clearance(m,q,.0015);record['reactions']=certify_active_reactions(m,q,.0015);record['status']='pass';steps.append(record);p=q;break
 except ValueError as error:
  record['status']='fail';record['error']=str(error);failure=getattr(error,'report',None);record['reactionFailure']=failure;steps.append(record)
  if failure is None:break
 p=q
out={'sourceSHA256':s['sourceSHA256'],'colliderSHA256':hashlib.sha256((w/'native-collision-vertical.json').read_bytes()).hexdigest(),'method':'Bounded unit-tension chain Jacobian residual correction, generated only from actual material-force residual; independent full 3D recertification, no hand points or tolerance change.','steps':steps}
(w/'force-settling-probe.json').write_text(json.dumps(out,indent=2)+'\n');print([(x['status'],x['maxStepM'],x.get('error')) for x in steps])
