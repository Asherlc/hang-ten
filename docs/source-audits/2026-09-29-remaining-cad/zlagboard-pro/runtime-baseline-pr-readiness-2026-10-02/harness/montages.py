from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
s=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/ios-diagnosis');o=s/'review-montages';o.mkdir(exist_ok=True)
b=json.loads(__import__('subprocess').check_output(['rtk','proxy','python3','Tools/HangboardCAD/board_manifest.py','--package','zlagboard-pro']));font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20)
def sheet(items,path):
 canvas=Image.new('RGB',(560*len(items),1250),'#f8f7f2');d=ImageDraw.Draw(canvas)
 for i,(label,p) in enumerate(items):
  im=Image.open(p).convert('RGB');im.thumbnail((540,1190));canvas.paste(im,(i*560+(560-im.width)//2,55));d.text((i*560+10,15),label,font=font,fill='#172820')
 canvas.save(path)
contacts=[c['id'] for c in b['contacts']]
for i in range(0,len(contacts),3):sheet([(c,s/'captures'/(c+'.png')) for c in contacts[i:i+3]],o/('selections-'+str(i//3+1)+'.png'))
orbits=sorted((s/'captures').glob('*-orbit.png'))
for i in range(0,len(orbits),3):sheet([(p.stem.replace('-orbit',''),p) for p in orbits[i:i+3]],o/('orbits-'+str(i//3+1)+'.png'))
sheet([(c,s/'captures'/(c+'.png')) for c in ['top-jug-left','top-sloper-32-left','edge-20-left']],s/'app-review.png')
