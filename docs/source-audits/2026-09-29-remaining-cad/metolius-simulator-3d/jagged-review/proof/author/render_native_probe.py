from pathlib import Path
import json,sys,numpy as np
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author';sys.path.insert(0,str(root/'Tools/HangboardCAD'));from preview import _render
m=json.loads((w/'probe-body-mesh.json').read_text());p=np.asarray(m['p'])[np.asarray(m['t'])];n=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);lens=np.linalg.norm(n,axis=1);lens[lens==0]=1;n/=lens[:,None]
for view in ['front','side','top','oblique']:
 pp,nn=p,n
 if view=='oblique':
  depth=np.array([.7,-1,.52]);depth/=np.linalg.norm(depth);right=np.cross(depth,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,depth);rot=np.stack([right,-depth,up],axis=1);pp=p@rot;nn=n@rot
 _render(pp,nn,'front' if view=='oblique' else view,w/'review'/('native-probe-'+view+'.png'),size=(1200,650))
print('rendered native probe')
