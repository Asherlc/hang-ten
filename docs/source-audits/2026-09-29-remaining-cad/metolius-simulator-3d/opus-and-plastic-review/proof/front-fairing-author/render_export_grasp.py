from pathlib import Path
import sys,json,hashlib,numpy as np
from PIL import Image,ImageDraw
from pxr import Usd,UsdGeom
w=Path(__file__).resolve().parent;out=w/'export-grasp-review';out.mkdir(exist_ok=True);sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'));from preview import _render
rows=[(0,'Center jug center'),(30,'Center jug side'),(46,'Center jug root'),(95,'Round sloper core'),(148.1,'Round-flat join'),(210,'Flat sloper core'),(185.1,'Flat blend end'),(235,'Flat outer core'),(293,'Outer jug center')]
report={}
for version in ['original-9449','candidate']:
 asset=w/version/'assets/primary.usdz';stage=Usd.Stage.Open(str(asset));cache=UsdGeom.XformCache();meshes={}
 for prim in stage.Traverse():
  if not prim.IsA(UsdGeom.Mesh):continue
  m=UsdGeom.Mesh(prim);p=np.asarray(m.GetPointsAttr().Get(),dtype=float);mat=np.asarray(cache.GetLocalToWorldTransform(prim));q=np.c_[p,np.ones(len(p))]@mat;q=np.stack([q[:,0],-q[:,2],q[:,1]],axis=1)*1000;idx=np.asarray(m.GetFaceVertexIndicesAttr().Get()).reshape(-1,3);meshes[prim.GetName()]=q[idx]
 body_only=next(v for k,v in meshes.items() if k.startswith('body_'));body=np.concatenate(list(meshes.values()));n=np.cross(body[:,1]-body[:,0],body[:,2]-body[:,0]);length=np.linalg.norm(n,axis=1);length[length==0]=1;n/=length[:,None]
 for name,depth in [('rear-oblique',[.7,1,.65]),('high-front',[.2,-1,1.4]),('rear-center',[0,1,.5])]:
  depth=np.array(depth,dtype=float);depth/=np.linalg.norm(depth);right=np.cross(depth,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,depth);rot=np.stack([right,-depth,up],axis=1);_render(body@rot,n@rot,'front',out/(version+'-'+name+'.png'),size=(1400,800))
 im=Image.new('RGB',(1800,1620),'white');draw=ImageDraw.Draw(im);draw.text((20,15),version.upper()+' | EXACT USDZ TRIANGLE SECTIONS | DARK = BODY, ORANGE = TAGGED TOP CONTACT',fill='black')
 for i,(x,label) in enumerate(rows):
  ox=(i%3)*600+60;oy=(i//3)*520+75
  def xy(p):return (ox+(-p[0]+5)*4,oy+(230-p[1])*4)
  for f in range(0,101,20):
   xx,_=xy((-f,230));draw.line([(xx,oy),(xx,oy+440)],fill='#dddddd');draw.text((xx-5,oy+445),str(f),fill='#555555')
  for z in range(130,231,20):
   _,yy=xy((0,z));draw.line([(ox,yy),(ox+440,yy)],fill='#dddddd');draw.text((ox-30,yy),str(z),fill='#555555')
  selected=[('body',body)]+[(k,v) for k,v in meshes.items() if k.startswith('contact_') and ('jug_' in k or 'sloper_' in k)]
  ids=[]
  for name,tri in selected:
   candidates=tri[(tri[:,:,0].min(axis=1)<=x+1e-8)&(tri[:,:,0].max(axis=1)>=x-1e-8)];found=False
   for t in candidates:
    hits=[]
    for a,b in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])]:
     da,db=a[0]-x,b[0]-x
     if abs(da)<1e-8:hits.append(a[1:])
     if da*db<0:hits.append((a+(b-a)*(-da)/(db-da))[1:])
    unique=[]
    for p in hits:
     if not any(np.linalg.norm(p-q)<1e-7 for q in unique):unique.append(p)
    if len(unique)<2:continue
    a,b=unique[:2]
    if max(a[1],b[1])<125 or min(a[1],b[1])>230:continue
    draw.line([xy(a),xy(b)],fill='#334155' if name=='body' else '#de6b20',width=2 if name=='body' else 4);found=True
   if found and name!='body':ids.append(name.removeprefix('contact_').replace('_','-'))
  draw.text((ox,oy-25),label+' | X = '+str(x)+' mm',fill='black');draw.text((ox,oy+465),'Forward from rear wall (mm) | vertical = Z mm',fill='black');draw.text((ox,oy+480),', '.join(ids),fill='#b54e00')
 im.save(out/(version+'-grasp-sections.png'));report[version]={'modelSHA256':hashlib.sha256(asset.read_bytes()).hexdigest(),'descriptorSHA256':hashlib.sha256((asset.parent/'primary.model.json').read_bytes()).hexdigest(),'sourceSHA256':hashlib.sha256((w/version/'metolius-simulator-3d.FCStd').read_bytes()).hexdigest(),'meshCount':len(meshes),'bodyNodeTriangleCount':len(body_only),'completeShellTriangleCount':len(body)}
for name in ['rear-oblique','high-front','rear-center','grasp-sections']:
 a=Image.open(out/('original-9449-'+name+'.png'));b=Image.open(out/('candidate-'+name+'.png'));panel=Image.new('RGB',(a.width+b.width,max(a.height,b.height)+35),'white');draw=ImageDraw.Draw(panel);draw.text((20,10),'ORIGINAL COMMITTED 9449 EXACT USDZ',fill='black');draw.text((a.width+20,10),'FINAL FRONT FAIRING EXACT USDZ',fill='black');panel.paste(a,(0,35));panel.paste(b,(a.width,35));panel.save(out/('comparison-'+name+'.png'))
report['method']='Exact USDZ mesh-plane intersections and complete exported shell views, including all 30 separately exported contact surfaces. Orange denotes actual exported top-contact meshes. CPU triangle-face shading, no reference-image processing.';report['images']={str(p.relative_to(w)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.png'))};(w/'export-grasp-provenance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='images'},indent=2))
