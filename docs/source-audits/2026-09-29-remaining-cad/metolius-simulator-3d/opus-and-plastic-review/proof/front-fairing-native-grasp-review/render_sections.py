from pathlib import Path
import json,sys,numpy as np
from PIL import Image,ImageDraw
w=Path(__file__).resolve().parent;r=json.loads((w/'native-sections.json').read_text());im=Image.new('RGB',(1800,1620),'white');draw=ImageDraw.Draw(im)
draw.text((20,15),'FROZEN b722 FRONT-FAIRED NATIVE CANDIDATE | NATIVE CAD SECTIONS | DARK = SOLID OUTLINE, ORANGE = TAGGED TOP CONTACT',fill='black')
for i,row in enumerate(r['sections']):
 ox=(i%3)*600+60;oy=(i//3)*520+75
 def xy(y,z):return (ox+(-y+5)*4,oy+(230-z)*4)
 for forward in range(0,101,20):
  x,_=xy(-forward,230);draw.line([(x,oy),(x,oy+440)],fill='#dddddd');draw.text((x-5,oy+445),str(forward),fill='#555555')
 for z in range(130,231,20):
  _,yy=xy(0,z);draw.line([(ox,yy),(ox+440,yy)],fill='#dddddd');draw.text((ox-30,yy),str(z),fill='#555555')
 for loop in row['bodyLoops']:
  for e in loop:
   chunks=[];chunk=[]
   for y,z in e:
    if 125<=z<=230:chunk.append(xy(y,z))
    elif chunk:chunks.append(chunk);chunk=[]
   if chunk:chunks.append(chunk)
   for chunk in chunks:
    if len(chunk)>1:draw.line(chunk,fill='#334155',width=3)
 ids=[]
 for c in row['contacts']:
  if not any(s in c['id'] for s in ['jug','sloper']):continue
  ids.append(c['id'])
  for e in c['edges']:draw.line([xy(y,z) for y,z in e],fill='#de6b20',width=5)
 draw.text((ox,oy-25),row['label']+' | X = '+str(row['xMm'])+' mm',fill='black');draw.text((ox,oy+465),'Forward depth (mm); height Z (mm) on vertical axis',fill='black');draw.text((ox,oy+480),', '.join(ids),fill='#b54e00')
im.save(w/'native-grasp-sections.png')
sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'));from preview import _render
m=json.loads((w/'native-body-mesh.json').read_text());p=np.asarray(m['p'])[np.asarray(m['t'])];n=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);lens=np.linalg.norm(n,axis=1);lens[lens==0]=1;n/=lens[:,None]
for name,depth in [('rear-oblique',[.7,1,.65]),('high-front',[.2,-1,1.4]),('rear-center',[0,1,.5])]:
 depth=np.array(depth,dtype=float);depth/=np.linalg.norm(depth);right=np.cross(depth,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,depth);rot=np.stack([right,-depth,up],axis=1);_render(p@rot,n@rot,'front',w/(name+'.png'),size=(1400,800))
print('Rendered sections and three whole native views')
