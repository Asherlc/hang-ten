from pathlib import Path
import json,sys,hashlib,numpy as np,trimesh
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'));sys.path.insert(0,str(w/'reaction-sampling-probe'))
from native_cord_guides import certify_active_reactions,certify_groove_traversal,certify_bore_entry
from native_cord_routes import checked_clearance
s=json.loads((w/'native-collision-vertical.json').read_text());m=trimesh.Trimesh(s['vertices'],s['triangles'],process=False);original=np.array(json.loads((w/'optimizer-convergence-probe/candidate-000.json').read_text())['path']);p=original.copy();p[:,2]=0
r={'sourceSHA256':s['sourceSHA256'],'colliderSHA256':hashlib.sha256((w/'native-collision-vertical.json').read_bytes()).hexdigest(),'nativePlane':'spanned by longitudinal guide and bore axes, runtime Z=0','maximumProjectionM':float(abs(original[:,2]).max()),'leads':{}}
for side,sign in [('Right',1)]:
 q=p.copy();q[:,0]=sign*abs(q[:,0]);row={'path':q.tolist()}
 try:
  row['clearance']=checked_clearance(m,q,.0015);row['seating']=certify_groove_traversal(q,.0015,s['nativeCordFeatures'][side+'VerticalCordGroove'],1,q[-1]);row['entry']=certify_bore_entry(q,.0015,s['nativeCordFeatures'][side+'VisibleMouth'],[sign,0,0],.0002);row['reactions']=certify_active_reactions(m,q,.0015);row['status']='pass'
 except ValueError as e:row['status']='fail';row['error']=str(e);row['failureReport']=getattr(e,'report',None)
 r['leads'][side]=row
(w/'reaction-sampling-probe/right-certificate.json').write_text(json.dumps(r,indent=2)+'\n');print({k:(v['status'],v.get('error')) for k,v in r['leads'].items()})
