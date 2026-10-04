from pathlib import Path
import hashlib,json,os,subprocess,time,traceback
root=Path.cwd(); scratch=root/'.context/placid-badger-cad-second-half/runtime-resume-2026-10-02/ios-uninterrupted'; out=scratch/'captures'
out.mkdir(exist_ok=True); logs=out/'commands'; logs.mkdir(exist_ok=True)
uid=(scratch/'simulator-ready').read_text().strip(); commands=[]; checks=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)]; n=len(commands); commands.append(cmd)
 r=subprocess.run(cmd,env=env,capture_output=True,timeout=120)
 (logs/f'{n:03d}-stdout.txt').write_bytes(r.stdout); (logs/f'{n:03d}-stderr.txt').write_bytes(r.stderr)
 (logs/'index.json').write_text(json.dumps(commands,indent=2)+'\n')
 r.check_returncode(); return r.stdout.decode()
def flat(nodes):
 rows=[]
 for node in nodes:
  if node.get('AXLabel') or node.get('AXUniqueId'): rows.append({k:node.get(k) for k in ('type','AXLabel','AXUniqueId','AXValue','frame')})
  rows.extend(flat(node.get('children',[])))
 return rows
def ready(contact=None):
 for attempt in range(60):
  try: rows=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)))
  except subprocess.CalledProcessError:
   time.sleep(1); continue
  ids={r['AXUniqueId'] for r in rows if r['AXUniqueId']}
  assert 'boardModel.unavailable' not in ids
  contacts={i for i in ids if i.startswith('boardModel.contact.')}
  if contacts and 'boardModel.loading' not in ids and (contact is None or 'boardDetail.selectedHold.'+contact in ids):
   assert len(contacts)==expected_count,(len(contacts),contacts)
   return rows
  time.sleep(1)
 raise RuntimeError('No ready board selection '+str(contact))
def capture(name,contact=None):
 rows=ready(contact); (out/(name+'-accessibility.json')).write_text(json.dumps(rows,indent=2)+'\n')
 time.sleep(1); run('xcrun','simctl','io',uid,'screenshot',out/(name+'.png'))
 checks.append({'image':name+'.png','contactID':contact,'contactsAvailable':expected_count,'selectedAXConfirmed':contact is not None})
 print(name,flush=True); return rows
def launch(contact=None):
 env=dict(os.environ,SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='zlagboard.pro',SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_DETAIL='1')
 if contact: env['SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_HOLD_ID']=contact
 run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env); time.sleep(2)
def frames(rows): return {r['AXUniqueId']:r['frame'] for r in rows if (r['AXUniqueId'] or '').startswith('boardModel.contact.')}
board=json.loads(subprocess.check_output(['rtk','proxy','python3','Tools/HangboardCAD/board_manifest.py','--package','zlagboard-pro']))
contacts=[c['id'] for c in board['contacts']]
priority=['top-jug-left','top-jug-right','edge-20-left','top-sloper-32-left','edge-incut-10-center','edge-15-left','edge-incut-15-left','edge-35-center']
contacts=[c for c in priority if c in contacts]+[c for c in contacts if c not in priority]
expected_count=len(contacts)
# Fixed board with no package positions. Representative orbits expose top and pocket depth.
resolved={c['id']:'fixed-primary' for c in board['contacts']}
representatives={}
(out/'resolved-capture-plan.json').write_text(json.dumps({'resolvedPositionByContact':resolved,'orbitRepresentatives':representatives},indent=2)+'\n')
try:
 launch(); capture('default')
 for contact in contacts:
  launch(contact); before=capture(contact,contact)
  if contact in representatives:
   f=next(r['frame'] for r in before if r['AXUniqueId']=='boardDetail.map')
   run('/opt/homebrew/bin/axe','swipe','--start-x',f['x']+f['width']*.4,'--start-y',f['y']+f['height']*.5,'--end-x',f['x']+f['width']*.58,'--end-y',f['y']+f['height']*.5,'--duration','1.0','--udid',uid)
   after=capture(representatives[contact]+'-orbit',contact)
   assert frames(before)!=frames(after),'orbit did not change projected contact frames'
   checks[-1]['actualOrbitVerified']=True
except Exception:
 (out/'failure.txt').write_text(traceback.format_exc()); raise
finally:
 package=root/'Hangboards/zlagboard-pro'; built=scratch/('DerivedData-'+root.name)/'Build/Products/Debug-iphonesimulator/HangTen.app'
 record={'owner':root.name,'simulator':uid,'device':'iPhone 17 Pro','runtime':'iOS26.5','boardID':'zlagboard.pro','sourceSHA256':sha(package/'zlagboard-pro.FCStd'),'modelSHA256':sha(package/'assets/primary.usdz'),'descriptorSHA256':sha(package/'assets/primary.model.json'),'builtBinarySHA256':sha(built/'HangTen'),'surfaceFinish':board['presentations'][0]['media']['display'].get('surfaceFinish','neutral'),'checks':checks,'commands':commands,'humanGeometryAcceptance':'pending user review #21','limits':'Full-frame fresh app screenshots and AX identity/orbit probes; no factory geometry or ergonomic certification.'}
 (out/'validation.json').write_text(json.dumps(record,indent=2)+'\n')
