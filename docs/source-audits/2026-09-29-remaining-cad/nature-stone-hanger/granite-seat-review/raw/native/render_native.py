from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
w=Path(__file__).resolve().parent;m=json.loads((w/'native-preview-meshes.json').read_text())
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',22);small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',17)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a):return [x/math.sqrt(dot(a,a))for x in a]
def panel(body,contact,view,title,W=620,H=620):
 im=Image.new('RGB',(W,H),'#f6f5f1');d=ImageDraw.Draw(im);d.text((22,14),title,font=font,fill='#202020')
 cam=norm(view);right=norm(cross([0,0,1],cam)) if view!=(0,0,1) else [1,0,0];up=cross(cam,right)
 # For front view, +X points right.
 if view==(0,-1,0):right=[1,0,0];up=[0,0,1]
 scale=min(W,H-55)/127;triangles=[];light=norm([-.3,-.5,.8])
 for key,stone in [(body,False),(contact,True)]:
  data=m[key];vs=data['vertices'];ps=[(W/2+dot(v,right)*scale,H/2+28-dot(v,up)*scale,dot(v,cam))for v in vs]
  for t in data['triangles']:
   a,b,c=[vs[i]for i in t];n=cross([b[i]-a[i]for i in range(3)],[c[i]-a[i]for i in range(3)]);length=math.sqrt(dot(n,n))
   if length<1e-9:continue
   luminance=.65+.35*abs(dot([x/length for x in n],light));base=83 if stone else 210;v=int(base*luminance);color=(v,v,v)
   xyz=[ps[i]for i in t];depth=sum(z[2]for z in xyz)/3+(0.003 if stone else 0);triangles.append((depth,[(q[0],q[1])for q in xyz],color))
 for _,points,color in sorted(triangles,key=lambda x:x[0]):d.polygon(points,fill=color)
 return im
views=[((0,-1,0),'FRONT'),((-1,0,0),'SIDE'),((0,0,1),'TOP')]
out=Image.new('RGB',(1860,1280),'#f6f5f1');d=ImageDraw.Draw(out);d.text((22,1244),'Whole native CAD views. Grey = combined body; dark = granite contact. Preview colors only; no model materials.',font=small,fill='#333333')
for row,(body,contact,label)in enumerate([('priorBody','priorGraniteContact','PRIOR'),('body','graniteContact','CORRECTED')]):
 for col,(view,title)in enumerate(views):out.paste(panel(body,contact,view,label+' / '+title),(col*620,row*620))
out.save(w/'native-front-side-top.png')
out=Image.new('RGB',(1240,670),'#f6f5f1');out.paste(panel('priorBody','priorGraniteContact',(-1,-2,.6),'PRIOR / OBLIQUE'),(0,0));out.paste(panel('body','graniteContact',(-1,-2,.6),'CORRECTED / OBLIQUE'),(620,0));ImageDraw.Draw(out).text((22,632),'Whole native CAD; granite semantic ownership shown dark. No photographic measurements.',font=small,fill='#333333');out.save(w/'native-oblique.png')
s=json.loads((w/'native-sections.json').read_text());im=Image.new('RGB',(1100,730),'white');d=ImageDraw.Draw(im)
for col,(body,stone,title)in enumerate([('priorBody','priorStone','PRIOR'),('body','stone','CORRECTED')]):
 ox=col*550+275;oy=360;scale=5.2;d.text((col*550+22,18),title+' / CENTER SECTION X=0',font=font,fill='black')
 for key,color,width in [(body,'#747474',4),(stone,'#bb351c',2)]:
  for line in s[key]:d.line([(ox+v[1]*scale,oy-v[2]*scale)for v in line],fill=color,width=width)
 d.text((col*550+80,650),'Front (negative Y) at left',font=small,fill='black')
d.text((25,697),'Grey: unified body boundary. Red: complete stone section, including seated hidden surfaces.',font=small,fill='black');im.save(w/'native-center-section.png')
print('native-front-side-top.png; native-oblique.png; native-center-section.png')
