from pathlib import Path
import json,hashlib,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path.cwd();W=ROOT/'.context/placid-badger/nature-stone-review9/vertical-groove-correction';BEFORE=W/'before';AFTER=W/'isolated-root/Hangboards/nature-stone-hanger';OUT=W/'previous-to-vertical-previews';OUT.mkdir(exist_ok=True);(OUT/'panels').mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();data=[json.loads((p/'suspension.json').read_text()) for p in [BEFORE,AFTER]];plan=json.loads((W.parent/'pose-review/per-contact-pose-plan.json').read_text());poses=[p['positionID'] for p in plan['poses']]
assert set(data[1]['suspension']['canonicalPoses'])==set(poses)
helper=ROOT/'.context/placid-badger/cad-raster-boards/render_reviews.py';ns={};exec(helper.read_text().split('for folder in sorted(base.iterdir()):')[0],ns);preview=ns['preview']
sys.path.insert(0,str(ROOT/'Tools/HangboardPackages/src'));from hangboard_packages.board_catalog import _load_model_suspension,_validate_model_suspension
models=[];descriptors=[]
for pkg,doc in zip([BEFORE,AFTER],data):
 descriptor=json.loads((pkg/'assets/primary.model.json').read_text());assert descriptor['modelSHA256']==doc['modelSHA256']==sha(pkg/'assets/primary.usdz');descriptors.append(descriptor)
 parsed=_load_model_suspension(doc['suspension'],str(pkg));bounds=descriptor['modelBounds'];_validate_model_suspension(parsed,model_bounds=(tuple(bounds['min']),tuple(bounds['max'])),nodes={n['nodeID']:n['role'] for n in descriptor['nodes']},position_ids=set(doc["suspension"]["canonicalPoses"]))
 model=preview.read_usdz(pkg/'assets/primary.usdz');points,normals=preview._triangles(model);points=np.stack([points[...,0],points[...,2],-points[...,1]],axis=-1)/1000;normals=np.stack([normals[...,0],normals[...,2],-normals[...,1]],axis=-1);models.append((points,normals,model))
def rotate(q,p):
 q=np.asarray(q);t=2*np.cross(q[:3],p);return p+q[3]*t+np.cross(q[:3],t)
def native(p):return np.stack([p[...,0],-p[...,2],p[...,1]],axis=-1)*1000
def cylinder(a,b,r):
 v=b-a;v/=np.linalg.norm(v);seed=np.eye(3)[np.argmin(abs(v))];u=np.cross(v,seed);u/=np.linalg.norm(u);w=np.cross(v,u);N=24
 rings=[np.array([p+r*(np.cos(t)*u+np.sin(t)*w) for t in np.arange(N)*2*np.pi/N]) for p in [a,b]]
 return np.asarray([tri for i in range(N) for tri in ([rings[0][i],rings[1][i],rings[0][(i+1)%N]],[rings[0][(i+1)%N],rings[1][i],rings[1][(i+1)%N]],[a,rings[0][(i+1)%N],rings[0][i]],[b,rings[1][i],rings[1][(i+1)%N]])])
render_source='def render('+helper.read_text().split('def render(')[1].split('preview._render=render')[0];render_source=render_source.replace('u0,u1=u.min(),u.max();v0,v1=v.min(),v.max();','u0,u1,v0,v1=limits;')
render_source=render_source.replace('rgb[y0:y1+1,x0:x1+1][mask]=g[mask,None].astype(np.uint8)',"rgb[y0:y1+1,x0:x1+1][mask]=(np.array([232,112,35])*(.65+.35*g[mask,None]/255)).astype(np.uint8) if highlight[i] else g[mask,None].astype(np.uint8)")
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20);small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17);records=[];pose_evidence={}
for pose_id in poses:
 scenes=[];evidence=[];node_id=pose_id.replace('-','_')+'_mesh_001'
 for i,(doc,(points,normals,scene_model),descriptor) in enumerate(zip(data,models,descriptors)):
  selected=np.concatenate([np.full(len(node['triangles']),name==node_id,dtype=bool) for name,node in scene_model['nodes'].items()]);assert selected.any(),node_id
  setup=doc['suspension'];pose=setup['canonicalPoses'][pose_id];q=pose['rotation'];translation=np.asarray(pose['translation']);bounds=descriptor['modelBounds'];anchor=(np.asarray(bounds['min'])+np.asarray(bounds['max']))/2;anchor[1]=bounds['max'][1];anchor+=np.asarray(setup['anchor']['offsetFromBoardBounds'])
  body=rotate(q,points);body_normals=rotate(q,normals);tubes=[];paths={}
  for strand in setup['strands']:
   # Same canonical rigid transform and fixed-anchor prefix used by the repository CAD-routed solver.
   path=np.vstack([anchor-translation,rotate(q,np.asarray(pose['wrappedRoutes'][strand['id']]))]);paths[strand['id']]={'pointsBodyCenteredWorldM':path.tolist(),'radiusM':strand['radius'],'lengthM':float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum()),'restLengthM':strand['restLength']}
   for a,b in zip(path,path[1:]):
    if np.linalg.norm(b-a)>1e-6:tubes.append(cylinder(a,b,strand['radius']))
  tube=np.concatenate(tubes);scenes.append((native(np.concatenate([body,tube])),np.concatenate([native(body_normals)/1000,np.zeros_like(tube)]),native(body),np.r_[selected,np.zeros(len(tube),dtype=bool)]))
  evidence.append({'modelSHA256':doc['modelSHA256'],'rotation':q,'camera':pose['camera'],'translation':pose['translation'],'anchorWorldM':anchor.tolist(),'supportToPosedBodyTopGapM':float(anchor[1]-translation[1]-body[...,1].max()),'routes':paths})
 pose_evidence[pose_id]={'before':evidence[0],'after':evidence[1]}
 for view in ['front','side','top']:
  for mode in ['full','detail']:
   fit=np.concatenate([scene[2] if mode=='detail' else scene[0] for scene in scenes]);u,v,_=ns['project'](fit,view);pad=15 if mode=='detail' else 0;limits=(u.min()-pad,u.max()+pad,v.min()-pad,v.max()+pad);frames=[]
   for i,(tri,norm,_,highlight) in enumerate(scenes):
    scope=dict(ns,limits=limits,highlight=highlight);exec(render_source,scope);panel=OUT/'panels'/(pose_id+'-'+view+'-'+mode+'-'+str(i)+'.png');scope['render'](tri,norm,view,panel,size=(850,700));frame=Image.new('RGB',(850,760),'white');frame.paste(Image.open(panel),(0,60));draw=ImageDraw.Draw(frame);label='Previous: transverse-guide cord' if i==0 else 'Corrected: vertical-seat 120 mm leads';draw.text((15,8),label,font=font,fill='black');draw.text((15,36),pose_id+' / '+view+' / '+mode+' / orange = selected',font=small,fill='black');frames.append(frame)
   pair=Image.new('RGB',(1700,760),'white');pair.paste(frames[0],(0,0));pair.paste(frames[1],(850,0));name=pose_id+'-'+view+'-'+mode+'.png';pair.save(OUT/name);records.append({'poseID':pose_id,'view':view,'mode':mode,'image':name,'sha256':sha(OUT/name),'commonViewportLimitsMM':list(map(float,limits))})
 print(pose_id+' complete',flush=True)

proof={'sourceSHA256':sha(AFTER/'nature-stone-hanger.FCStd'),'modelSHA256':sha(AFTER/'assets/primary.usdz'),'descriptorSHA256':sha(AFTER/'assets/primary.model.json'),'beforeSidecarSHA256':sha(BEFORE/'suspension.json'),'afterSidecarSHA256':sha(AFTER/'suspension.json'),'method':'Complete actual USDZ plus exact solver cached routes and fixed support; unchanged 3 mm diameter, same paired viewport. Technical z-buffer; no source image processing.','poseEvidence':pose_evidence,'comparisons':records,'humanAcceptance':'pending'}
(OUT/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n')
canvas=Image.new('RGB',(1700,8*380+60),'white');draw=ImageDraw.Draw(canvas);draw.text((20,10),'STONE HANGER: rejected short routing / native groove-guided candidate | orange contact',font=font,fill='black')
for i,pose_id in enumerate(poses):canvas.paste(Image.open(OUT/(pose_id+'-front-detail.png')).resize((850,380),Image.Resampling.LANCZOS),((i%2)*850,60+(i//2)*380))
canvas=canvas.crop((0,0,1700,4*380+60));canvas.save(OUT/'eight-hold-orientation-overview.png')
proof['overview']={'path':'eight-hold-orientation-overview.png','sha256':sha(OUT/'eight-hold-orientation-overview.png')};proof['nativeBearingEvidence']={'path':str(W.parent/'pose-review/per-contact-pose-plan.json'),'sha256':sha(W.parent/'pose-review/per-contact-pose-plan.json')};(OUT/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Forty-eight complete paired views rendered, all eight actual selected contact nodes.')
