from pathlib import Path
import sys,json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from pxr import Usd,UsdGeom,UsdShade
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-functional-correction';out=w/'export-review';out.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'Tools/HangboardCAD'))
from preview import _render
report={}
for version in ['original-9449','intermediate-21ca3','candidate']:
 asset=w/version/'assets/primary.usdz';stage=Usd.Stage.Open(str(asset));cache=UsdGeom.XformCache();parts=[];nodes=[]
 for prim in stage.Traverse():
  assert not prim.IsA(UsdShade.Material) and not prim.IsA(UsdShade.Shader)
  if not prim.IsA(UsdGeom.Mesh):continue
  assert not UsdShade.MaterialBindingAPI(prim).GetDirectBindingRel().GetTargets()
  mesh=UsdGeom.Mesh(prim);p=np.asarray(mesh.GetPointsAttr().Get(),dtype=float);m=np.asarray(cache.GetLocalToWorldTransform(prim));q=np.concatenate([p,np.ones((len(p),1))],axis=1)@m;q=np.stack([q[:,0],-q[:,2],q[:,1]],axis=1)*1000
  counts=np.asarray(mesh.GetFaceVertexCountsAttr().Get());assert np.all(counts==3)
  idx=np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1,3);parts.append(q[idx]);nodes.append(prim.GetName())
 points=np.concatenate(parts);normals=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]);lens=np.linalg.norm(normals,axis=1);lens[lens==0]=1;normals/=lens[:,None]
 for view in ['front','side','top','oblique','raking']:
  p,n=points,normals
  if view in ['oblique','raking']:
   depth=np.array([.7,-1,.52] if view=='oblique' else [1,-.65,.24]);depth/=np.linalg.norm(depth);right=np.cross(depth,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,depth);rot=np.stack([right,-depth,up],axis=1);p=points@rot;n=normals@rot
  _render(p,n,'front' if view in ['oblique','raking'] else view,out/(version+'-'+view+'.png'),size=(1200,650))
 report[version]={'triangleCount':len(points),'nodeCount':len(nodes),'boundsNativeMm':{'min':points.reshape(-1,3).min(axis=0).tolist(),'max':points.reshape(-1,3).max(axis=0).tolist()},'materialCount':0,'shaderCount':0,'hashes':{str(p.relative_to(w/version)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [w/version/'metolius-simulator-3d.FCStd',asset,w/version/'assets/primary.model.json']}}
for view in ['front','side','top','oblique','raking']:
 panel=Image.new('RGB',(3600,700),'white');draw=ImageDraw.Draw(panel)
 for i,version in enumerate(['original-9449','intermediate-21ca3','candidate']):
  panel.paste(Image.open(out/(version+'-'+view+'.png')),(1200*i,50));draw.text((20+1200*i,15),['ORIGINAL COMMITTED 9449','INTERMEDIATE 21CA3 GRASP ISSUE','FUNCTIONAL CORRECTION EXACT EXPORT 46DF0C'][i]+' | METOLIUS SIMULATOR 3-D | '+view.upper(),fill='black')
 panel.save(out/('comparison-'+view+'.png'))
report['reviewViews']=['front','side','top','oblique','raking'];report['renderer']='Shared preview.py Lambert triangle-face rendering at matching view and size; oblique applies fixed orthographic rotation.'
(w/'package-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
