"""CPU geometry-only previews of immutable USDZ files, with hash-bound provenance.

No geometry is authored, repaired, re-exported, or substituted by this renderer.
Original normal channels and USD sidedness are used; textures and app suspension
are deliberately not simulated. The output is not a native SceneKit screenshot.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from numba import njit
from PIL import Image, ImageDraw, ImageFont
_models_dir = str(Path(__file__).resolve().parent.parent / "Tools" / "HangboardModels")
if _models_dir not in sys.path:
    sys.path.insert(0, _models_dir)
from usdz_readback import read_scene
from remove_mounting_bores import package_board_bytes

import os
COMMIT = os.environ.get('RENDER_COMMIT','ef07a5fb04104d5f0a5ed3accc4c6ae918e02529')
LABEL=os.environ.get('RENDER_VARIANT','Baseline')
VIEWS = {'front': (0., 0., 1.), 'rear': (0., 0., -1.), 'oblique': (0.55, 0.40, 1.)}

@njit(cache=True)
def raster(tri, shade, active, width, height):
    zbuf = np.full((height, width), -1.e30, np.float32)
    pixels = np.full((height, width), 248., np.float32)
    for i in range(len(tri)):
        if not active[i]:
            continue
        a,b,c = tri[i,0], tri[i,1], tri[i,2]
        xmin=max(0, int(math.floor(min(a[0],b[0],c[0]))))
        xmax=min(width-1,int(math.ceil(max(a[0],b[0],c[0]))))
        ymin=max(0,int(math.floor(min(a[1],b[1],c[1]))))
        ymax=min(height-1,int(math.ceil(max(a[1],b[1],c[1]))))
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1.e-10:
            continue
        for y in range(ymin,ymax+1):
            for x in range(xmin,xmax+1):
                xx,yy=x+.5,y+.5
                u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
                v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
                w=1-u-v
                if u>=-1.e-6 and v>=-1.e-6 and w>=-1.e-6:
                    z=u*a[2]+v*b[2]+w*c[2]
                    if z>zbuf[y,x]:
                        zbuf[y,x]=z
                        pixels[y,x]=u*shade[i,0]+v*shade[i,1]+w*shade[i,2]
    return pixels

def unit(a):
    a=np.asarray(a,dtype=np.float64)
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1.e-16)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def render_one(root: Path, slug: str):
    package=root/'Hangboards'/slug
    model=package/'assets/primary.usdz'
    before=sha(model)
    stage,meshes=read_scene(model)
    vertices=[];normals=[];face_normals=[];sidedness=[]
    for m in meshes:
        tris=m['world'][m['f']]
        face=unit(np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]))
        if m['mesh'].GetOrientationAttr().Get()=='leftHanded': face=-face
        if 'normals' in m['channels']:
            n=m['channels']['normals']@np.linalg.inv(m['matrix'][:3,:3]).T
            bad=np.linalg.norm(n,axis=-1)<1.e-12
            n[bad]=np.broadcast_to(face[:,None,:],n.shape)[bad]
        else: n=np.broadcast_to(face[:,None,:],tris.shape).copy()
        vertices.append(tris);normals.append(unit(n));face_normals.append(face)
        sidedness.append(np.full(len(tris),bool(m['mesh'].GetDoubleSidedAttr().Get())))
    tris=np.concatenate(vertices);normals=np.concatenate(normals)
    face=np.concatenate(face_normals);double=np.concatenate(sidedness)
    centre=(tris.min((0,1))+tris.max((0,1)))/2
    tris=tris-centre
    board=json.loads(package_board_bytes(package) or b'{}')
    title=f"{board.get('manufacturer','')} {board.get('name',slug)}".strip()
    if title.lower().count(board.get('manufacturer','').lower())>1:
        title=board.get('name',slug)
    target=root/'Previews'/slug;target.mkdir(parents=True,exist_ok=True)
    try:
        title_font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',25)
        small_font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    except OSError:
        title_font=ImageFont.load_default()
        small_font=ImageFont.load_default()
    report={'board':slug,'modelPath':model.relative_to(root).as_posix(),'modelSHA256':before,
      'descriptorSHA256':sha(model.with_suffix('.model.json')),'commit':COMMIT,
      'triangleCount':len(tris),'renderer':'CPU depth buffer; neutral geometry-only shading',
      'rendererSHA256':sha(Path(__file__)),'views':[]}
    W,H=1440,740
    for label,normal in VIEWS.items():
        view=unit(np.asarray(normal));right=unit(np.cross([0.,1.,0.],view));up=unit(np.cross(view,right))
        basis=np.stack([right,up,view],1)
        p=tris@basis
        bounds=np.stack([p.min((0,1)),p.max((0,1))])
        extent=bounds[1]-bounds[0]
        scale=min((W-100)/max(extent[0],1.e-8),(H-130)/max(extent[1],1.e-8))
        p[:,:,0]=(p[:,:,0]-bounds[:,0].mean())*scale+W/2
        p[:,:,1]=-(p[:,:,1]-bounds[:,1].mean())*scale+(H+25)/2
        facing=np.einsum('ij,j->i',face,view)>1.e-12
        ns=normals.copy()
        flip=(np.einsum('ijk,k->ij',ns,view)<0)&double[:,None]
        ns[flip]*=-1
        light=unit(view*.85+up*.60-right*.5)
        fill=unit(view*.6-up*.15+right*.85)
        levels=45+145*np.maximum(0,np.einsum('ijk,k->ij',ns,light))+40*np.maximum(0,np.einsum('ijk,k->ij',ns,fill))
        pix=raster(np.ascontiguousarray(p),np.ascontiguousarray(levels),facing|double,W,H)
        img=Image.fromarray(np.uint8(np.clip(pix,0,255))).convert('RGB')
        d=ImageDraw.Draw(img)
        d.rectangle((0,0,W,56),fill=(255,255,255))
        d.text((25,14),title+' — '+label.title()+' / '+LABEL,fill=(32,32,32),font=title_font)
        d.rectangle((0,H-35,W,H),fill=(255,255,255))
        d.text((25,H-25),f'{LABEL}  /  {len(tris):,} triangles  /  USDZ {before[:16]}  /  Matched camera + light; geometry-only, not iOS',fill=(75,75,75),font=small_font)
        dest=target/f'{label}.png';img.save(dest,optimize=True)
        report['views'].append({'name':label,'path':dest.relative_to(root).as_posix(),'sha256':sha(dest),'cameraFromDirection':normal})
    if sha(model)!=before: raise RuntimeError('renderer modified the model')
    (target/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(slug,len(tris),'triangles;',len(report['views']),'views',flush=True)
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--boards',nargs='+',required=True)
    args=ap.parse_args()
    for slug in args.boards:render_one(args.root,slug)
