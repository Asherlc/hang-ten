"""Rebuild the Evolv Long mesh from hand-authored metric section and rear-cavity data.
No source images are opened by this code. Source photographs remain research evidence only.
"""
from pathlib import Path
import argparse,json,numpy as np
from geometry import build
from asset_io import write_glb,atomic_bytes

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    cfg=json.loads(Path(__file__).with_name('geometry-config.json').read_text());a.output.mkdir(parents=True,exist_ok=True)
    mesh,parts,labels,info=build(cfg)
    result=write_glb(a.output/(cfg['slug']+'.glb'),parts,color=cfg['color'],roughness=cfg['roughness'],metadata={
        'model':cfg['name'],'revision':cfg['revision'],'sourceFrame':'metres X-right Y-rear Z-up',
        'exportConversion':'(x,y,z)->(x,z,-y)','origin':'rear-bottom-centre','fixedWallMounted':True,
        'physicalFrontInGLTF':[0,0,1],'displayModelNotManufacturingCAD':True})
    np.savez_compressed(a.output/'editable-assembled-mesh.npz',vertices=mesh.vertices/1000,faces=mesh.faces,face_labels=labels,vertex_normals=mesh.vertex_normals)
    # PLY preserves editable assembled surface; JSON/NPZ preserve contact partition.
    mesh.vertices/=1000
    atomic_bytes(a.output/'assembled-source-z-up.ply',mesh.export(file_type='ply'))
    atomic_bytes(a.output/'build-result.json',json.dumps(result|{'geometry':info},indent=2).encode())
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
