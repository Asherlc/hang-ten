from pathlib import Path
import sys,json,time,numpy as np
from configs import get
from geometry import build
from asset_io import write_glb,atomic_bytes
root=Path(__file__).resolve().parents[1]
slug=sys.argv[1]; cfg=get(slug); out=root/'models'/slug; (out/'source').mkdir(parents=True,exist_ok=True)
atomic_bytes(out/'source'/'geometry-config.json',json.dumps(cfg,indent=2).encode())
start=time.time(); mesh,parts,labels,info=build(cfg)
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,info
np.savez_compressed(out/'source'/'editable-assembled-mesh.npz',vertices=mesh.vertices/1000,faces=mesh.faces,face_labels=labels,vertex_normals=mesh.vertex_normals)
# PLY is an editable standard geometry source in source Z-up, separate contact IDs in JSON/NPZ.
source=mesh.copy(); source.vertices/=1000; atomic_bytes(out/'source'/'assembled-source-z-up.ply',source.export(file_type='ply'))
result=write_glb(out/(slug+'.glb'),parts,color=cfg['color'],metadata={'model':cfg['name'],'revision':cfg['revision'],'sourceFrame':'metre X right, Y rear, Z up','exportConversion':'(x,y,z) -> (x,z,-y)','physicalFrontInGLTF':[0,0,1],'origin':'rear-bottom-centre','fixedWallMounted':True})
result['geometry']=info; result['seconds']=time.time()-start
atomic_bytes(out/'build-result.json',json.dumps(result,indent=2).encode())
print(json.dumps(result,indent=2),flush=True)
