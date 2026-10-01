import sys,json,shutil,html
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'Tools/HangboardCAD'));import preview
base=ROOT/'.context/placid-badger/cad-raster-boards';dest=ROOT/'docs/source-audits/2026-09-29-remaining-cad'
origproject=preview._project
def project(p,view):
 if view=='top':return p[:,:,0],p[:,:,1],-p[:,:,2]
 if view=='side':return p[:,:,1],p[:,:,2],-p[:,:,0]
 return origproject(p,view)
preview._project=project
def triangles(model):
 rows=[];normals=[]
 for node in model['nodes'].values():
  pts=preview._native(node);tri=np.asarray(node['triangles'],dtype=int)
  if not len(tri):continue
  n=np.asarray(node['normals']);n=np.stack([n[:,0],-n[:,2],n[:,1]],axis=1);rows.append(pts[tri]);normals.append(n[tri])
 return np.concatenate(rows),np.concatenate(normals)
preview._triangles=triangles
def render(points,normals,view,path,size=(900,650)):
 width,height=size;u,v,depth=project(points,view);u0,u1=u.min(),u.max();v0,v1=v.min(),v.max();pad=.04*max(u1-u0,v1-v0);u0-=pad;u1+=pad;v0-=pad;v1+=pad;scale=min((width-1)/(u1-u0),(height-1)/(v1-v0));sx=(u-u0)*scale+((width-1)-(u1-u0)*scale)/2;sy=(v1-v)*scale+((height-1)-(v1-v0)*scale)/2
 zbuf=np.full((height,width),np.inf);rgb=np.full((height,width,3),255,dtype=np.uint8);shade=np.clip(normals@preview.LIGHT,0,1);greys=(55+shade*185).astype(np.uint8)
 for i in range(len(points)):
  x=sx[i];y=sy[i];den=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
  if abs(den)<1e-8:continue
  x0=max(0,int(np.floor(x.min())));x1=min(width-1,int(np.ceil(x.max())));y0=max(0,int(np.floor(y.min())));y1=min(height-1,int(np.ceil(y.max())))
  if x0>x1 or y0>y1:continue
  xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5);a=((y[1]-y[2])*(xx-x[2])+(x[2]-x[1])*(yy-y[2]))/den;b=((y[2]-y[0])*(xx-x[2])+(x[0]-x[2])*(yy-y[2]))/den;c=1-a-b;z=a*depth[i,0]+b*depth[i,1]+c*depth[i,2];target=zbuf[y0:y1+1,x0:x1+1];mask=(a>=-1e-6)&(b>=-1e-6)&(c>=-1e-6)&(z<target);target[mask]=z[mask];g=a*greys[i,0]+b*greys[i,1]+c*greys[i,2];rgb[y0:y1+1,x0:x1+1][mask]=g[mask,None].astype(np.uint8)
 Image.fromarray(rgb).save(path)
preview._render=render
for folder in sorted(base.iterdir()):
 assets=folder/'candidate-assets';slug=folder.name
 if not assets.is_dir():continue
 if len(sys.argv)>1 and slug not in sys.argv[1:]:continue
 out=folder/'review';out.mkdir(exist_ok=True);final=dest/slug/'review';final.mkdir(exist_ok=True)
 board=json.loads((ROOT/'.context/placid-badger/baseline'/slug/'board.json').read_text());rows=[]
 for pres in board['presentations']:
  path=ROOT/'Hangboards'/slug/pres['media']['assetPath'];target=final/('prior-'+pres['id']+path.suffix)
  if path.is_file():shutil.copy2(path,target)
  if target.is_file():rows.append(('<strong>Prior raster — '+html.escape(pres['name'])+'</strong>',target.name))
 for asset in assets.glob('*.usdz'):
  model=preview.read_usdz(asset);points,normals=preview._triangles(model)
  for view in ['front','side','top','rear','oblique']:
   pts=points.copy();ns=normals.copy();v=view
   if view=='rear':pts[:,:,0]*=-1;pts[:,:,1]*=-1;ns[:,:,0]*=-1;ns[:,:,1]*=-1;v='front'
   elif view=='oblique':
    a=np.radians(-24);b=np.radians(18);rotZ=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]);rotX=np.array([[1,0,0],[0,np.cos(b),-np.sin(b)],[0,np.sin(b),np.cos(b)]]);rot=rotX@rotZ;pts=pts@rot.T;ns=ns@rot.T;v='front'
   name=asset.stem+'-'+view+'.png';preview._render(pts,ns,v,out/name,size=(900,650));shutil.copy2(out/name,final/name);rows.append((html.escape(asset.stem+' — '+view),name))
 text='<html><meta charset="utf-8"><title>'+html.escape(slug)+' CAD comparison</title><style>body{font:16px system-ui;margin:28px;background:#eee;color:#111}main{display:grid;grid-template-columns:repeat(3,minmax(240px,1fr));gap:16px}figure{margin:0;background:white;padding:12px}img{width:100%;height:360px;object-fit:contain}figcaption{padding:10px}h1{font-size:24px}</style><h1>'+html.escape(slug)+'</h1><p>Prior committed raster compared with native CAD front, side, top, rear and oblique views. No prior CAD side/top asset existed. Uniform material-free geometry; cord review follows CAD route solving. These are technical candidate views, pending user review.</p><main>'+''.join('<figure><img src="'+name+'"><figcaption>'+caption+'</figcaption></figure>' for caption,name in rows)+'</main></html>'
 (final/'index.html').write_text(text);print(slug,len(rows),flush=True)
