from pathlib import Path
import subprocess,json,os,time,hashlib,atexit,signal,re,traceback
n=Path(__file__).parent.parent;out=n/'captures';out.mkdir();logs=out/'commands';logs.mkdir()
owned=json.loads((n/'ios/ownership.json').read_text());uid=owned['simulatorUUID'];owner=owned['owner'];commands=[];checks=[];children=[];appPID=None;appPIDs=[];start=time.monotonic();deadline=start+420
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=json.loads((n/'source-reference.json').read_text());parity=json.loads((n/'build/parity.json').read_text());assert parity['allEqual'];assert all(sha(x['path'])==x['sha256'] for x in source['files']+parity['checks'])
board=json.loads((n/'generated-board.json').read_text());contacts=[c['id'] for c in board['contacts']];assert len(contacts)==28 and not board.get('positions');assert owner=='placid-badger-cad-second-half'
priority=['top-jug-left','top-jug-right','top-sloper-32-left','top-sloper-20-left','top-sloper-jug-center','edge-20-left','edge-15-left','edge-incut-15-left','edge-incut-10-center','edge-35-center'];contacts=priority+[c for c in contacts if c not in priority]
representatives={'top-jug-left':'jug','top-sloper-32-left':'sloper','edge-15-left':'flat','edge-incut-15-left':'incut','edge-incut-10-center':'shallow-incut'}
(out/'prospective-plan.json').write_text(json.dumps(dict(contacts=contacts,fixedPresentation='primary',orbitRepresentatives=representatives,physicalTap='AX projected center followed by actual targeted-gesture pickedContact diagnostic; no accessibilityAction invoked',reset='Relaunch same requested selection creates explicit fresh-view reset; no reset button claimed',boundSeconds=420,noPixelMeasurement=True),indent=2)+'\n')
def stop(p):
 if p.poll() is None:
  p.terminate()
  try:p.wait(timeout=2)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
atexit.register(lambda:[stop(p) for p in children])
def interrupted(sig,frame):raise InterruptedError(sig)
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
def write(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
def run(args,env=None,cleanup=False,allow_failure=False):
 if not cleanup:assert time.monotonic()<deadline,'420s hard bound'
 i=len(commands);row=dict(command=['rtk','proxy',*map(str,args)],startEpoch=time.time());commands.append(row)
 with (logs/f'{i:03d}.stdout').open('xb') as a,(logs/f'{i:03d}.stderr').open('xb') as b:
  p=subprocess.Popen(row['command'],env=env,stdout=a,stderr=b);children.append(p);row['pid']=p.pid;write('commands.json',commands)
  try:r=p.wait(timeout=30)
  finally:stop(p)
 row.update(exitStatus=r,endEpoch=time.time());write('commands.json',commands)
 if r and not allow_failure:raise RuntimeError('Command failed; raw output retained')
 return (logs/f'{i:03d}.stdout').read_text()
def flat(nodes):
 r=[]
 for x in nodes:r.append(x);r.extend(flat(x.get('children',[])))
 return r
def ready(contact):
 for _ in range(8):
  rows=flat(json.loads(run(['/opt/homebrew/bin/axe','describe-ui','--udid',uid])))
  ids={x.get('AXUniqueId') for x in rows};assert 'boardModel.unavailable' not in ids
  if 'boardModel.loading' not in ids and 'boardDetail.selectedHold.'+contact in ids:
   assert len([i for i in ids if i and i.startswith('boardModel.contact.')])==28
   return rows
  time.sleep(.5)
 raise RuntimeError('Expected loaded selection not ready: '+contact)
def diagnostic(rows):
 return next((x.get('AXValue','') for x in rows if x.get('AXUniqueId')=='boardModel.renderDiagnostic'),'')
def capture(name,contact,extra=None):
 rows=ready(contact);time.sleep(.6);rows=ready(contact);write(name+'-ax.json',rows)
 run(['xcrun','simctl','io',uid,'screenshot',out/(name+'.png')])
 checks.append(dict(image=name+'.png',sha256=sha(out/(name+'.png')),contactID=contact,contactsAvailable=28,selectedAXConfirmed=True,diagnostic=diagnostic(rows),**(extra or {})));write('checks.json',checks);print(name,flush=True);return rows
def launch(contact):
 global appPID
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')}
 flags=dict(HANGTEN_REVIEW_BOARD_ID='zlagboard.pro',HANGTEN_REVIEW_BOARD_DETAIL='1',HANGTEN_REVIEW_BOARD_HOLD_ID=contact,HANGTEN_REVIEW_BOARD_DIAGNOSTICS='1')
 env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()})
 response=run(['xcrun','simctl','launch','--terminate-running-process','--stdout='+str((out/(contact+'-app.stdout')).resolve()),'--stderr='+str((out/(contact+'-app.stderr')).resolve()),uid,'com.hangten.training','-workoutAudioCuesEnabled','NO'],env)
 match=re.search(r':\s*(\d+)\s*$',response);assert match;appPID=int(match.group(1));appPIDs.append(appPID);write('app-ownership.json',dict(owner=owner,uuid=uid,appPIDs=appPIDs,launchFlags=flags));time.sleep(1)
def frames(rows):return {x['AXUniqueId']:x['frame'] for x in rows if x.get('AXUniqueId','').startswith('boardModel.contact.')}
error=None
try:
 for contact in contacts:
  launch(contact);rows=ready(contact);f=next(x['frame'] for x in rows if x.get('AXUniqueId')=='boardModel.contact.'+contact)
  run(['/opt/homebrew/bin/axe','tap','-x',f['x']+f['width']/2,'-y',f['y']+f['height']/2,'--udid',uid]);time.sleep(.5)
  rows=capture(contact,contact)
  d=diagnostic(rows);assert 'tapRevision=1' in d and 'pickedContact='+contact in d,'Actual targeted pick missing: '+contact+' '+d
  checks[-1]['physicalTargetedTapConfirmed']=True;write('checks.json',checks)
  if contact in representatives:
   f=next(x['frame'] for x in rows if x.get('AXUniqueId')=='boardDetail.map')
   run(['/opt/homebrew/bin/axe','swipe','--start-x',f['x']+f['width']*.4,'--start-y',f['y']+f['height']*.55,'--end-x',f['x']+f['width']*.53,'--end-y',f['y']+f['height']*.40,'--duration','.5','--udid',uid]);time.sleep(.5)
   after=capture(representatives[contact]+'-orbit',contact);assert frames(after)!=frames(rows),'No projected camera change'
   checks[-1]['actualOrbitConfirmed']=True;write('checks.json',checks)
   launch(contact);reset=capture(representatives[contact]+'-fresh-view-reset',contact);assert frames(reset)==frames(rows),'Fresh-view projected camera did not restore'
   checks[-1]['freshViewResetConfirmed']=True;write('checks.json',checks)
except BaseException:error=traceback.format_exc();(out/'failure.txt').write_text(error)
finally:
 cleanup=dict(owner=owner,uuid=uid)
 try:
  if appPID:run(['xcrun','simctl','terminate',uid,'com.hangten.training'],cleanup=True,allow_failure=True)
  absent=[]
  for p in appPIDs:
   text=run(['ps','-p',p,'-o','pid=,comm='],cleanup=True,allow_failure=True);absent.append(not text and commands[-1]['exitStatus']==1)
  cleanup.update(allOwnedAppPIDsAbsent=all(absent),appPIDs=appPIDs,passed=all(absent));write('cleanup.json',cleanup)
 except BaseException:cleanup['failure']=traceback.format_exc();cleanup['passed']=False;write('cleanup.json',cleanup)
 frozen=all(sha(x['path'])==x['sha256'] for x in source['files']+parity['checks'])
 write('completion.json',dict(completed=error is None,expectedContacts=28,capturedContacts=len({x['contactID'] for x in checks if x.get('physicalTargetedTapConfirmed')}),totalImages=len(checks),sourceAndPackageParityPreserved=frozen,visualResult='PENDING_WHOLE_IMAGE_REVIEW',error=error,cleanupPassed=cleanup.get('passed')))
if error or not cleanup.get('passed') or not frozen:raise SystemExit(1)
