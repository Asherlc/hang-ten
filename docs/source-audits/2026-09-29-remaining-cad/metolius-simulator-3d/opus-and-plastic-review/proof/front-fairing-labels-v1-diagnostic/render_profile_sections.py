from pathlib import Path
from PIL import Image,ImageDraw
import json
w=Path(__file__).resolve().parent;d=json.loads((w/'author-native-check.json').read_text());im=Image.new('RGB',(1800,870),'white');dr=ImageDraw.Draw(im);dr.text((25,15),'NATIVE FRONT FAIRING | source '+d['sourceSHA256'][:12]+' | blue = prior 3ff3; orange = corrected | no image measurements',fill='black')
for col,title in enumerate(['Lower front profile: forward depth','Lower front normal tilt (degrees)','Actual final BodySolid section X=40']):
 ox=60+col*600;oy=80;dr.text((ox,oy-30),title,fill='black')
 top=150 if col<2 else 225;scale=4.3 if col<2 else 2.85
 for z in range(0,top+1,25):
  yy=oy+(top-z)*scale;dr.line([(ox,yy),(ox+460,yy)],fill='#ddd');dr.text((ox-25,yy),str(z),fill='#555')
 for x in range(0,101,20):
  xx=ox+x*4.2;dr.line([(xx,oy),(xx,oy+650)],fill='#ddd');dr.text((xx,oy+665),str(x),fill='#555')
 def pt(x,z):return(ox+x*4.2,oy+(top-z)*scale)
 if col<2:
  for version,color in [('before3ff3','#2b6b9b'),('candidate','#d36622')]:
   for curve in d['profiles'][version]:
    pts=[pt(-s['yz'][0] if col==0 else abs(s['tiltDegrees']),s['yz'][1]) for s in curve['samples'] if 0<=s['yz'][1]<=150]
    if len(pts)>1:dr.line(pts,fill=color,width=3)
 else:
  for e in next(row for row in d['sections'] if row['xMM']==40)['bodyEdges']:
   if len(e)>1:dr.line([pt(-y,z) for y,z in e],fill='#d36622',width=3)
 dr.text((ox,oy+700),'Vertical: native Z (mm)',fill='#333')
dr.text((30,835),'Existing depth anchors retained. Shared nonzero native tangents below Z135 remove the repeated full-width slope resets; top grip solid is unchanged.',fill='black');im.save(w/'native-profile-sections.png')
