"""Hash-guarded actual USDZ/exact cached route capsule previews; no native solving."""
from pathlib import Path
import argparse, hashlib, html, json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path.cwd()
LANE = ROOT / '.context/placid-badger/port-cord-physics'
BEFORE = LANE / 'before-package'
PACKAGE = ROOT / 'Hangboards/frictitious-port-a-board'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--after', type=Path)
parser.add_argument('--approved-after-sha256')
parser.add_argument('--out', type=Path)
parser.add_argument('--prepare-only', action='store_true')
parser.add_argument('--provisional', action='store_true')
args = parser.parse_args()
baseline = json.loads((LANE / 'baseline.json').read_text())
for rel, digest in baseline['hashes'].items():
    assert sha(BEFORE / rel) == digest, rel
    if rel != 'suspension.json':
        assert sha(PACKAGE / rel) == digest, rel
old = json.loads((BEFORE / 'suspension.json').read_text())
descriptor = json.loads((BEFORE / 'assets/primary.model.json').read_text())
bounds = descriptor['modelBounds']
def support(setup):
    point = (np.asarray(bounds['min']) + np.asarray(bounds['max'])) / 2
    point[1] = bounds['max'][1]
    return point + np.asarray(setup['anchor']['offsetFromBoardBounds'])
runtime = json.loads((LANE / 'runtime/runtime-route-review.json').read_text())
assert np.allclose(support(old['suspension']), runtime['quantitative']['supportWorld'], atol=1e-12)
assert np.allclose(support(old['suspension']), [0, .17, 0], atol=1e-12)
poses = list(old['suspension']['canonicalPoses'])
assert len(poses) == 6 and len(old['suspension']['strands']) == 4
prepared = {'owner': 'placid-badger', 'status': 'Prepared; awaiting explicitly approved after SHA',
    'baselineCommit': baseline['baselineCommit'], 'beforePackageSHA256': baseline['hashes'],
    'runtimeProofSHA256': sha(LANE / 'runtime/runtime-route-review.json'),
    'beforeSupportWorldM': support(old['suspension']).tolist(), 'poseIDs': poses,
    'rendererSHA256': sha(Path(__file__)), 'views': ['front','side','top','oblique'],
    'method': 'Actual unchanged USDZ with all four exact-route lead strands. Canonical quaternion and translation applied in world coordinates; actual fixed support prepended. Capsule union: 24-sided segment cylinders and 24x12 endpoint spheres. No route smoothing. Common world-space fitting for both versions, native triangle z-buffer; no cropping/alignment.',
    'limits': 'Technical capsule preview, not an app screenshot or independent native clearance/physics certificate. Parent/native author own all six pose physical certificates.'}
if args.prepare_only:
    (LANE / 'previews/prepared.json').write_text(json.dumps(prepared, indent=2)+'\n')
    print(json.dumps(prepared, indent=2))
    sys.exit(0)
assert args.after and args.approved_after_sha256 and args.out
assert sha(args.after) == args.approved_after_sha256
after = json.loads(args.after.read_text())
assert after['modelSHA256'] == old['modelSHA256'] == baseline['hashes']['assets/primary.usdz']
assert set(poses) == set(after['suspension']['canonicalPoses'])
for a,b in zip(old['suspension']['strands'], after['suspension']['strands'], strict=True):
    for key in ['id','kind','radius','restLength']:
        assert a[key] == b[key], key
    assert a['kind'] == 'lead'
for pose_id in poses:
    a = old['suspension']['canonicalPoses'][pose_id]
    b = after['suspension']['canonicalPoses'][pose_id]
    assert a['rotation'] == b['rotation'] and a['camera'] == b['camera']
    assert set(a['wrappedRoutes']) == set(b['wrappedRoutes'])
    assert all(a['wrappedRoutes'][k][-1] == b['wrappedRoutes'][k][-1] for k in a['wrappedRoutes'])
OUT = args.out
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'panels').mkdir(exist_ok=True)
helper = ROOT / '.context/placid-badger/cad-raster-boards/render_reviews.py'
ns = {}
exec(helper.read_text().split('for folder in sorted(base.iterdir()):')[0], ns)
preview = ns['preview']
model = preview.read_usdz(BEFORE/'assets/primary.usdz')
points, normals = preview._triangles(model)
points = np.stack([points[...,0],points[...,2],-points[...,1]],axis=-1)/1000
normals = np.stack([normals[...,0],normals[...,2],-normals[...,1]],axis=-1)
sys.path.insert(0,str(ROOT/'Tools/HangboardPackages/src'))
from hangboard_packages.board_catalog import _load_model_suspension, _validate_model_suspension
for document in [old,after]:
    parsed = _load_model_suspension(document['suspension'],str(PACKAGE))
    _validate_model_suspension(parsed, model_bounds=(tuple(bounds['min']),tuple(bounds['max'])),
        nodes={n['nodeID']:n['role'] for n in descriptor['nodes']}, position_ids=set(poses))
def rotate(q,p):
    q=np.asarray(q); t=2*np.cross(q[:3],p)
    return p+q[3]*t+np.cross(q[:3],t)
def native(p):
    return np.stack([p[...,0],-p[...,2],p[...,1]],axis=-1)
def cylinder(a,b,r):
    v=b-a; v=v/np.linalg.norm(v); seed=np.eye(3)[np.argmin(abs(v))]
    u=np.cross(v,seed); u/=np.linalg.norm(u); w=np.cross(v,u); n=24
    dirs=np.array([np.cos(t)*u+np.sin(t)*w for t in np.arange(n)*2*np.pi/n])
    rings=[a+r*dirs,b+r*dirs]
    return np.asarray([tri for i in range(n) for tri in (
        [rings[0][i],rings[1][i],rings[0][(i+1)%n]],
        [rings[0][(i+1)%n],rings[1][i],rings[1][(i+1)%n]])])
def sphere(center,r):
    rings=np.asarray([[center+r*np.array([np.sin(t)*np.cos(p),np.cos(t),np.sin(t)*np.sin(p)])
        for p in np.arange(24)*2*np.pi/24] for t in np.linspace(0,np.pi,13)])
    return np.asarray([tri for j in range(12) for i in range(24) for tri in (
        [rings[j,i],rings[j+1,i],rings[j,(i+1)%24]],
        [rings[j,(i+1)%24],rings[j+1,i],rings[j+1,(i+1)%24]])])
render_source='def render('+helper.read_text().split('def render(')[1].split('preview._render=render')[0]
render_source=render_source.replace('u0,u1=u.min(),u.max();v0,v1=v.min(),v.max();','u0,u1,v0,v1=limits;')
a,b=np.radians(-24),np.radians(18)
oblique=np.array([[1,0,0],[0,np.cos(b),-np.sin(b)],[0,np.sin(b),np.cos(b)]]) @ np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
records=[]; pose_evidence={}
for pose_id in poses:
    scenes=[]; evidence=[]
    for document in [old,after]:
        setup=document['suspension']; pose=setup['canonicalPoses'][pose_id]
        q=pose['rotation']; translation=np.asarray(pose['translation']); anchor=support(setup)
        body=rotate(q,points)+translation; body_normals=rotate(q,normals); tubes=[]; paths={}
        for strand in setup['strands']:
            path=np.vstack([anchor,rotate(q,np.asarray(pose['wrappedRoutes'][strand['id']]))+translation])
            paths[strand['id']]={'pointsWorldM':path.tolist(),'radiusM':strand['radius'],
                'lengthM':float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum()),'restLengthM':strand['restLength']}
            for first,last in zip(path,path[1:]):
                if np.linalg.norm(last-first)>1e-9: tubes.append(cylinder(first,last,strand['radius']))
            tubes.extend(sphere(point,strand['radius']) for point in path)
        tube=np.concatenate(tubes)
        scenes.append((native(np.concatenate([body,tube]))*1000,
            np.concatenate([native(body_normals),np.zeros_like(tube)])))
        evidence.append({'rotation':q,'translation':pose['translation'],'anchorWorldM':anchor.tolist(),
            'camera':pose['camera'],'routes':paths})
    pose_evidence[pose_id]={'before':evidence[0],'after':evidence[1]}
    for view in ['front','side','top','oblique']:
        camera_scenes=[(tri@oblique.T,norm@oblique.T) if view=='oblique' else (tri,norm) for tri,norm in scenes]
        projection='front' if view=='oblique' else view
        fit=np.concatenate([scene[0] for scene in camera_scenes]); u,v,_=ns['project'](fit,projection)
        limits=(u.min(),u.max(),v.min(),v.max()); pair=Image.new('RGB',(1700,810),'white')
        for i,(tri,norm) in enumerate(camera_scenes):
            scope=dict(ns,limits=limits); exec(render_source,scope)
            panel=OUT/'panels'/f'{pose_id}-{view}-{i}.png'
            scope['render'](tri,norm,projection,panel,size=(850,730))
            pair.paste(Image.open(panel),(850*i,80)); draw=ImageDraw.Draw(pair)
            label='Before: committed native routes' if i==0 else ('Candidate: ' if args.provisional else 'After: ')+'native routes'
            draw.text((850*i+15,10),label,font=font,fill='black')
            draw.text((850*i+15,40),pose_id+' / '+view+' / shared world frame',font=small,fill='black')
        name=f'{pose_id}-{view}.png'; pair.save(OUT/name)
        records.append({'poseID':pose_id,'view':view,'image':name,'sha256':sha(OUT/name),
            'commonWorldViewportMM':list(map(float,limits))})
    print(pose_id+' complete',flush=True)
proof=dict(prepared,status='Provisional native route preview' if args.provisional else 'Frozen native route preview; human review pending',
    afterSidecarSHA256=sha(args.after),afterSidecarPath=str(args.after),
    modelNodeIDs=sorted(model['nodes']),helperSHA256=sha(helper),poseEvidence=pose_evidence,
    comparisons=records,repositoryParserAndRouteValidationPassed=True)
(OUT/'render-provenance.json').write_text(json.dumps(proof,indent=2)+'\n')
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Port-A-Board cord review</title><style>body{font:16px system-ui;margin:24px}img{max-width:100%}</style><h1>Port-A-Board cord routing</h1><p>Actual unchanged USDZ; all four exact saved routes. Same world frame. Capsule previews are technical illustrations, not app captures. Native physical certificates retained separately.</p>'+''.join('<figure><img src="'+r['image']+'"><figcaption>'+html.escape(r['poseID']+' / '+r['view'])+'</figcaption></figure>' for r in records))
for rel,digest in baseline['hashes'].items():
    assert sha(BEFORE/rel)==digest
    if rel!='suspension.json': assert sha(PACKAGE/rel)==digest
assert sha(args.after)==args.approved_after_sha256
print('24 same-world-frame pairs complete; all six poses / four strands retained.')
