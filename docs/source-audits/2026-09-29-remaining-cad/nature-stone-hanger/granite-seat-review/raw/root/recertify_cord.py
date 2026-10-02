"""Recertify unchanged solver-generated routes after local insert geometry work."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import numpy as np
import trimesh

ROOT = Path.cwd()
LANE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'Tools/HangboardCAD'),str(ROOT/'Tools/HangboardPackages/src')]
from native_cord_guides import validate_guide_bindings, _certify_guided_paths
from solve_threaded_rope import rotate_inverse

sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source = json.loads((LANE/'native-collision-solid.json').read_text())
old = json.loads((LANE/'committed-before/suspension.json').read_text())
descriptor = json.loads((LANE/'assets/primary.model.json').read_text())
before_descriptor = json.loads((LANE/'committed-before/primary.model.json').read_text())
proof = json.loads((LANE/'independent-native-check.json').read_text())
assert proof['status']=='pass' and proof['outerCordBearingRegionPreserved']
assert source['sourceSHA256']==sha(LANE/'native-author/nature-stone-hanger.FCStd')
assert descriptor['modelBounds']==before_descriptor['modelBounds']
data = copy.deepcopy(old)
data['modelSHA256'] = descriptor['modelSHA256']
data['ropeSolver']['grooveGuides']['sourceSHA256'] = source['sourceSHA256']
features = validate_guide_bindings(data,source)
mesh = trimesh.Trimesh(source['vertices'],source['triangles'],process=False)
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
setup=data['suspension']; solver=data['ropeSolver']
radii={s['id']:s['radius'] for s in setup['strands']}
rests={s['id']:s['restLength'] for s in setup['strands']}
bounds=descriptor['modelBounds']
anchor=(np.array(bounds['min'])+np.array(bounds['max']))/2
anchor[1]=bounds['max'][1]
anchor+=np.array(setup['anchor']['offsetFromBoardBounds'])
poses={}
for pid,pose in setup['canonicalPoses'].items():
    support=rotate_inverse(pose['rotation'],anchor-np.array(pose['translation']))
    full={k:np.vstack([support,np.asarray(path,float)]) for k,path in pose['wrappedRoutes'].items()}
    minimums,ratios,certificates=_certify_guided_paths(mesh,full,radii,rests,features,
        solver['grooveGuides']['byPoseID'][pid],solver['terminalsByStrandID'],solver['clearance'])
    poses[pid]={'height':pose['translation'][1],'minimumClearance':minimums,
                'lengthRatios':ratios,'certificates':certificates}
    print('recertified',pid,flush=True)
assert len(poses)==8
text=(LANE/'committed-before/suspension.json').read_text()
assert text.count(old['modelSHA256'])==1
assert text.count(old['ropeSolver']['grooveGuides']['sourceSHA256'])==1
text=text.replace(old['modelSHA256'],data['modelSHA256']).replace(
    old['ropeSolver']['grooveGuides']['sourceSHA256'],source['sourceSHA256'])
assert json.loads(text)==data
assert data['suspension']==old['suspension'], 'No route, pose, or cord setting may change'
(LANE/'suspension.json').write_text(text)
report={'status':'pass','sourceSHA256':source['sourceSHA256'],
        'modelSHA256':descriptor['modelSHA256'],'sidecarSHA256':sha(LANE/'suspension.json'),
        'collisionSolidSHA256':sha(LANE/'native-collision-solid.json'),
        'nativeGuideHelperSHA256':sha(ROOT/'Tools/HangboardCAD/native_cord_guides.py'),
        'routeOrigin':'Unchanged prior native-solver output. Existing routes recertified against the freshly exported updated native solid; no route or hanging translation authored or reoptimized.',
        'basis':'Native outer cord-bearing material and guide/bore geometry unchanged; model bounds unchanged; every updated-solid clearance, groove traversal, bore entry, active material-facet reaction, strand intersection and rest-length gate rerun.',
        'poseCount':8,'branchCount':16,'poses':poses,
        'onlySidecarChangedFields':['modelSHA256','ropeSolver.grooveGuides.sourceSHA256'],
        'solverGeneratedRoutesAndTranslationsPreserved':True}
(LANE/'cord-recertification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'pass','poses':8,'branches':16,'sidecarSHA256':report['sidecarSHA256']}))
