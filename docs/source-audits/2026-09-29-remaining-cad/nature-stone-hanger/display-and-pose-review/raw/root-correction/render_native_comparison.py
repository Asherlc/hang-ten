from pathlib import Path
import json,hashlib,numpy as np
from PIL import Image,ImageDraw,ImageFont
root=Path.cwd();w=Path(__file__).resolve().parent;out=w/'native-previews';out.mkdir(exist_ok=True);helper=root/'.context/placid-badger/cad-raster-boards/render_reviews.py';ns={};exec(helper.read_text().split('for folder in sorted(base.iterdir()):')[0],ns);preview=ns['preview'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=preview.read_usdz(w/'before/assets/primary.usdz');a,an=preview._triangles(before);mesh=json.loads((w/'native-author/body-mesh.json').read_text());b=np.asarray(mesh['vertices'])[np.asarray(mesh['triangles'])];bn=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0]);bn/=np.linalg.norm(bn,axis=1)[:,None];bn=np.repeat(bn[:,None,:],3,axis=1)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20);images={}
for view in ['front','side','top','oblique']:
 panels=[]
 for index,(points,normals) in enumerate([(a,an),(b,bn)]):
  points=points.copy();normals=normals.copy();v=view
  if view=='oblique':
   az=np.radians(-32);ax=np.radians(14);rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]]);rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]]);rotation=rx@rz;points=points@rotation.T;normals=normals@rotation.T;v='front'
  path=out/((['before','after'][index])+'-'+view+'.png');ns['render'](points,normals,v,path,size=(900,650));panels.append(path);images[path.name]=sha(path)
 sheet=Image.new('RGB',(1800,700),'white');draw=ImageDraw.Draw(sheet)
 for index,path in enumerate(panels):
  sheet.paste(Image.open(path),(index*900,50));draw.text((index*900+15,12),('Prior committed model' if index==0 else 'Candidate: vertical cord groove + retained adjustment notches')+' / '+view,font=font,fill='black')
 target=out/('comparison-'+view+'.png');sheet.save(target);images[target.name]=sha(target)
proof={'sourceSHA256':mesh['sourceSHA256'],'nativeBodyMeshSHA256':sha(w/'native-author/body-mesh.json'),'beforeSourceSHA256':sha(w/'before/nature-stone-hanger.FCStd'),'beforeModelSHA256':sha(w/'before/assets/primary.usdz'),'beforeDescriptorSHA256':sha(w/'before/assets/primary.model.json'),'images':images,'method':'Whole native final-solid tessellation at unchanged 0.15 mm, compared with exact prior committed USDZ. Technical CPU normals; no materials/cords. No pixel inference or source-photo processing.','visualGate':'pending'}
(out/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n');print('four whole native comparisons complete')
