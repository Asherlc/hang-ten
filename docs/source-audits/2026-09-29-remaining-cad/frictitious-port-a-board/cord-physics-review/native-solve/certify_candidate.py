import json,hashlib,sys
from pathlib import Path
import numpy as np,trimesh
base=Path(__file__).resolve().parent;root=Path('/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger');sys.path.insert(0,str(root/'Tools/HangboardCAD'))
from native_cord_routes import checked_clearance,length
from solve_threaded_rope import rotate_inverse
from hangboard_packages.cord_paths import validate_cord_paths
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pkg=base/'isolated-root/Hangboards/frictitious-port-a-board';d=json.loads((pkg/'suspension.json').read_text());before=json.loads((base/'before-suspension.json').read_text());frozen=json.loads((base/'frozen-inputs.json').read_text());solid=json.loads((base/'solid-primary.json').read_text());desc=json.loads((pkg/'assets/primary.model.json').read_text())
assert solid['sourceSHA256']==frozen['packageBefore']['frictitious-port-a-board.FCStd']
assert d['suspension']['strands']==before['suspension']['strands'];assert d['suspension']['anchor']==before['suspension']['anchor'];assert d['suspension']['type']==before['suspension']['type'];assert d['suspension']['bodyNodeID']==before['suspension']['bodyNodeID'];assert d['modelSHA256']==before['modelSHA256']
assert d['ropeSolver']==dict(before['ropeSolver'],sectionPlane='anchor',pathSearch='aStar')
mesh=trimesh.Trimesh(vertices=solid['vertices'],faces=solid['triangles'],process=False);bounds=desc['modelBounds'];anchor=(np.array(bounds['min'])+np.array(bounds['max']))/2;anchor[1]=bounds['max'][1];anchor+=d['suspension']['anchor']['offsetFromBoardBounds'];radii={s['id']:s['radius'] for s in d['suspension']['strands']};rests={s['id']:s['restLength'] for s in d['suspension']['strands']};poses={}
for pid,pose in d['suspension']['canonicalPoses'].items():
 old=before['suspension']['canonicalPoses'][pid];assert pose['rotation']==old['rotation'] and pose['camera']==old['camera'];assert pose['translation'][::2]==old['translation'][::2]
 support=rotate_inverse(pose['rotation'],anchor-np.array(pose['translation']));paths={sid:np.vstack([support,route]) for sid,route in pose['wrappedRoutes'].items()};validate_cord_paths(paths,radii);rows={}
 for sid,path in paths.items():
  terminal=d['ropeSolver']['terminalsByStrandID'][sid]['points'][0];assert np.array_equal(path[-1],terminal);assert terminal==before['ropeSolver']['terminalsByStrandID'][sid]['points'][0];axis=np.array([0,0,1 if sid.endswith('front') else -1]);outward=float((path[-2]-path[-1])@axis);assert outward>1e-8;dist=length(path);assert dist<=rests[sid]*(1+1e-6)
  rows[sid]={'verticesIncludingSupport':len(path),'length':dist,'lengthRatio':dist/rests[sid],'certifiedClearance':checked_clearance(mesh,path,radii[sid]),'outwardMouthEntryDot':outward,'actualMouthPreserved':True}
 assert max(row['lengthRatio'] for row in rows.values())>=1-1e-6
 poses[pid]={'height':pose['translation'][1],'wholeTubeGate':'passed','strands':rows}
for name,expected in frozen['packageBefore'].items():
 assert sha(root/'Hangboards/frictitious-port-a-board'/name)==expected
 if name!='suspension.json':assert sha(pkg/name)==expected
for name,expected in frozen['solverHashes'].items():assert sha(root/name)==expected
for name,expected in frozen['allPackageHashes'].items():assert sha(root/name)==expected
report={'status':'passed','candidateSHA256':sha(pkg/'suspension.json'),'sourceSHA256':solid['sourceSHA256'],'modelSHA256':d['modelSHA256'],'sourceBoundSolidSHA256':sha(base/'solid-primary.json'),'authoringChange':'sectionPlane=anchor + pathSearch=aStar only; no collars/tightening','routeCertificates':sum(len(v['strands']) for v in poses.values()),'productionUnchanged':True,'poses':poses}
(base/'candidate-certificates.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='poses'},indent=2))
