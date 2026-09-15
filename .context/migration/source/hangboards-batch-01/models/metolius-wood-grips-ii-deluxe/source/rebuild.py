"""Rebuild this asset from its saved, editable numeric configuration."""
from pathlib import Path
import argparse,json,numpy as np
from geometry import build
from asset_io import write_glb,atomic_bytes
from render_glb import render
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--render',action='store_true');a=p.parse_args()
cfg=json.loads(Path(__file__).with_name('geometry-config.json').read_text());a.output.mkdir(parents=True,exist_ok=True)
mesh,parts,labels,info=build(cfg)
asset=a.output/(cfg['slug']+'.glb')
result=write_glb(asset,parts,color=cfg['color'],metadata={'model':cfg['name'],'revision':cfg['revision'],'sourceFrame':'metre X right, Y rear, Z up','exportConversion':'(x,y,z) -> (x,z,-y)','physicalFrontInGLTF':[0,0,1],'origin':'rear-bottom-centre','fixedWallMounted':True})
np.savez_compressed(a.output/'editable-assembled-mesh.npz',vertices=mesh.vertices/1000,faces=mesh.faces,face_labels=labels,vertex_normals=mesh.vertex_normals)
atomic_bytes(a.output/'build-result.json',json.dumps(result|{'geometry':info},indent=2).encode())
if a.render:render(asset,a.output/'renders',title=cfg['name'])
print(json.dumps(result,indent=2))
