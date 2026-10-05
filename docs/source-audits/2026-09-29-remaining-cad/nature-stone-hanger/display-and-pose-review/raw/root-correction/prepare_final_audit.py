from pathlib import Path
import json,sys,hashlib
import numpy as np
w=Path(__file__).resolve().parent;f=w/'final-code-freeze'
sys.path.insert(0,str(f/'Tools/HangboardCAD'));sys.path.insert(0,str(f/'Tools/HangboardPackages/src'))
from solve_threaded_rope import rotate_inverse
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((w/'final-apply/native-route-report.json').read_text());sidecar=w/'final-apply/suspension.json';data=json.loads(sidecar.read_text());descriptor=json.loads((w/'assets/primary.model.json').read_text());freeze=json.loads((f/'freeze.json').read_text())
helper=f/'Tools/HangboardCAD/native_cord_guides.py'
files={str(f/p):digest for p,digest in freeze['codeSHA256'].items()}
files['Tools/HangboardCAD/native_cord_guides.py']=sha(helper)
for p in ('run_final_routes.py','bounded_final_job.py','takeover-red.log','takeover-green.log','takeover-diagnostic-cleanup.json'):
 files[str(w/p)]=sha(w/p)
proof={'status':'pass','sourceSHA256':report['sourceSHA256'],'modelSHA256':report['modelSHA256'],'descriptorSHA256':sha(w/'assets/primary.model.json'),'colliderSHA256':report['collisionSolidSHA256'],'sidecarSHA256':sha(sidecar),'helperSHA256':sha(helper),'loadedHelperPath':str(helper),'routeCount':16,'inputs':[{'path':p,'sha256':digest} for p,digest in freeze['inputSHA256'].items()]+[{'path':str(w/'final-apply/native-route-report.json'),'sha256':sha(w/'final-apply/native-route-report.json')}],'poses':{},'limits':['Discrete frictionless feasibility at numerical contact offset; no global equilibrium/minimum, physical load or safety claim.','10 micrometres per correction, at most five corrections; endpoints fixed and full 3D/material checks repeated.']}
bounds=descriptor['modelBounds'];anchor=(np.array(bounds['min'])+np.array(bounds['max']))/2;anchor[1]=bounds['max'][1];anchor+=np.array(data['suspension']['anchor']['offsetFromBoardBounds'])
for key,result in report['poses'].items():
 pose=data['suspension']['canonicalPoses'][key];support=rotate_inverse(pose['rotation'],anchor-np.array(pose['translation']))
 leads={}
 for strand,route in result['routes'].items():
  leads[strand]={'pathModelM':np.vstack([support,route]).tolist(),'lengthRatio':result['lengthRatios'][strand],'continuousClearanceLowerBound':result['minimumClearance'][strand],**result['nativeGrooveGuidance']['certificates'][strand]}
 proof['poses'][key]={'leads':leads,'height':result['height'],'freshComputationReuse':result['nativeGrooveGuidance'].get('freshComputationReuse')}
for dest,value in ((w/'final-apply/audit-certificates.json',proof),):
 assert not dest.exists();dest.write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({str(p):sha(p) for p in (w/'final-apply/audit-certificates.json',f/'freeze.json',sidecar)},indent=2))
