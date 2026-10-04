from pathlib import Path
import os,sys,json,time,subprocess,hashlib,traceback
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
arm=sys.argv[1];assert arm in ['control','unmount']
# This file is preparation only until the parent supplies a reviewed release record.
releasePath=Path(sys.argv[2]);release=json.loads(releasePath.read_text())
assert release['runtimeAuthorized'] is True and release['arm']==arm
assert release['helperSHA256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
assert release['constructorMarkerAuditReady'] is True
assert release['structuralNavEventAuditReady'] is True
assert release['rootSourceRuntimeRelease'] is True
assert release['previousArmGatePassed'] is True
assert len(release['binarySHA256'])==64
out=base/('train-unmount-control-b-landscape');out.mkdir(exist_ok=False)
(out/'runtime-release.json').write_bytes(releasePath.read_bytes())
uid='BDCA0D77-94C2-4A97-900B-443F75C64691';commands=[];captures=[];transitions=[];tracefolder=None
start=time.monotonic();deadline=start+300;pending=[];known=set();scene=None

def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);t=time.time()
 try:r=subprocess.run(cmd,capture_output=True,env=env,timeout=max(.1,min(20,deadline-time.monotonic())))
 except subprocess.TimeoutExpired as e:
  (out/f'{n:03d}-stdout.txt').write_bytes(e.stdout or b'');(out/f'{n:03d}-stderr.txt').write_bytes(e.stderr or b'');commands.append({'command':cmd,'startEpoch':t,'endEpoch':time.time(),'timeout':True});raise
 (out/f'{n:03d}-stdout.txt').write_bytes(r.stdout);(out/f'{n:03d}-stderr.txt').write_bytes(r.stderr);commands.append({'command':cmd,'startEpoch':t,'endEpoch':time.time(),'exitStatus':r.returncode});r.check_returncode();return r.stdout.decode().strip()

def readrows():
 rows=[]
 for f in tracefolder.glob('events-*.jsonl'):
  for l in f.read_bytes().splitlines(keepends=True):
   if l.endswith(b'\n'):rows.append(json.loads(l))
 return rows

def save_trace():
 copies=[];rs=[]
 if tracefolder:
  for f in tracefolder.glob('events-*.jsonl'):
   raw=f.read_bytes();t=out/f.name;t.write_bytes(raw);copies.append({'source':str(f),'copy':str(t),'sha256':hashlib.sha256(raw).hexdigest()});assert raw.endswith(b'\n');rs.extend(json.loads(l) for l in raw.splitlines())
 if rs:assert all(r['complete'] for r in rs) and [r['sequence'] for r in rs]==list(range(1,len(rs)+1))
 (out/'trace-copy.json').write_text(json.dumps({'copies':copies,'records':len(rs),'completeContiguous':bool(rs),'copiedEpoch':time.time(),'includesSamplerEnd':any(r['event']=='sample-end' for r in rs)},indent=2)+'\n')

try:
 app=Path(run('xcrun','simctl','get_app_container',uid,'com.hangten.training','app'))
 binary=app/'HangTen.debug.dylib'
 actualBinarySHA=hashlib.sha256(binary.read_bytes()).hexdigest()
 (out/'installed-binary-gate.json').write_text(json.dumps({'path':str(binary),'sha256':actualBinarySHA,'expected':release['binarySHA256']},indent=2)+'\n')
 assert actualBinarySHA==release['binarySHA256'],'Installed binary mismatch; no launch permitted'
 data=Path(run('xcrun','simctl','get_app_container',uid,'com.hangten.training','data'))
 flags={'HANGTEN_REVIEW_BOARD_ID':'zlagboard.evo','HANGTEN_REVIEW_PLAN_ID':'research.max-hangs','HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC':'1','HANGTEN_REVIEW_DIAGNOSTIC_RUN':'placid-badger-cad-second-half-train-unmount-control-b','HANGTEN_REVIEW_LANDSCAPE':'1','HANGTEN_REVIEW_WORKOUT_BOUNDARY_CENSUS':'1'}
 flags['HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS']='1'
 flags['HANGTEN_REVIEW_PREDECESSOR_ATTACHMENT_CENSUS']='1'
 flags['HANGTEN_REVIEW_BOARD_DETACH_TRIAL']='1'
 flags['HANGTEN_REVIEW_DETACH_DISAPPEARING_BOARD_HOST']='1'
 if arm=='unmount':flags['HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT']='1'
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')};env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()})
 (out/'launch-review-environment.json').write_text(json.dumps(flags,indent=2)+'\n')
 (out/'protocol.json').write_text(json.dumps({'hardBoundSeconds':300,'plannedPhases':['active','preview','active'],'captureOffsetsAfterActualMutation':[.25,1,3,5],'afterLaunchUIAccess':'screenshots only; no AX queries/taps/Skip','externalTracePollingSeconds':.03,'routineUnchanged':True,'samplerLimit':'Existing120-iteration sampler remains; new identical both-arm boundary census on actual highlight-before/after supplies sparse late-phase app/window/placement evidence, not every capture instant','arm':arm,'startup':'Existing WorkoutAccessGate and production automatic-start policy in both arms; explicit DEBUG AUTOSTART omitted, fresh process/session; both arms normal launch plus existing workout deep link through original Train/navigation history; strict all-hand-host suppression enabled; Train board PRESENT; weak predecessor-attachment census, retained-model/tag trial and guarded disappearing Train root/camera detach common to both arms; unmount alone requests structural Train removal; bounded Train constructor/make+attachment readiness gate before openurl is a deliberate new common startup protocol; control must reproduce failure; perspective/old hand-OFF/camera/standalone/direct-root/root-navigation flags absent all arms'},indent=2)+'\n')
 tracefolder=data/'Documents'/('HighlightDiagnostic-'+flags['HANGTEN_REVIEW_DIAGNOSTIC_RUN']);assert not tracefolder.exists()
 run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env)
 # New shared startup protocol: observe existing events only; no AX/touch or UI write.
 readinessStart=time.monotonic();readinessStartEpoch=time.time();readinessDeadline=min(deadline,readinessStart+20);ready=None
 while time.monotonic()<readinessDeadline:
  readinessRows=readrows()
  makeByToken={r['sceneLifecycleToken']:r for r in readinessRows if r['event']=='view-make'}
  for r in readinessRows:
   for h in r.get('boardDetachTrial',{}).get('hosts',[]):
    token=h['sceneLifecycleToken'];make=makeByToken.get(token)
    weak=[w for w in r.get('boardLifetimeCensus',[]) if w['sceneLifecycleToken']==token]
    attached=(h['rootParentID']==h['cameraParentID']==h['recordedParentID']!='nil' and h['rootActualSceneID']==h['cameraActualSceneID']==h['recordedActualSceneID']!='nil')
    living=(len(weak)==1 and weak[0]['wrapperAlive'] and all(weak[0][e]['alive'] and weak[0][e]['isActive'] and weak[0][e]['parentEntityID']==h['recordedParentID'] and weak[0][e]['realitySceneID']==h['recordedActualSceneID'] for e in ['root','camera']))
    if make and r['sequence']>=make['sequence'] and h['trainMarked'] and h['currentOwner'] and h['modelRetainedForTrial'] and h['attachmentObserved'] and not h['disappeared'] and not h['detached'] and h['invalid']=='nil' and attached and living:
     ready=dict(makeRecord=make,attachmentRecord=r,trainToken=token,host=h,weak=weak[0],hostObservedEpoch=time.time());break
   if ready:break
  if ready:break
  time.sleep(.03)
 readiness=dict(boundSeconds=20,startEpoch=readinessStartEpoch,endEpoch=time.time(),elapsedSeconds=time.monotonic()-readinessStart,passed=ready is not None,evidence=ready,scope='Existing Train-tagged make and actual root/camera attachment observation only; not frame-presentation or backing-view-deallocation proof. No fixed delay fallback.')
 (out/'train-startup-readiness.json').write_text(json.dumps(readiness,indent=2)+'\n')
 assert ready is not None,'Train make+owned attachment readiness deadline expired; no openurl or fallback'
 openURLStart=time.time();run('xcrun','simctl','openurl',uid,'hangten://plan/research.max-hangs/workout');openURLEnd=time.time()
 (out/'workout-openurl-timing.json').write_text(json.dumps(dict(startEpoch=openURLStart,endEpoch=openURLEnd,readinessObservedEpoch=ready['hostObservedEpoch'],readinessBeforeOpenURL=ready['hostObservedEpoch']<=openURLStart),indent=2)+'\n')
 initialStart=time.time();run('xcrun','simctl','io',uid,'screenshot',out/'launch-initial.png');initialEnd=time.time()
 (out/'launch-initial-capture.json').write_text(json.dumps(dict(startEpoch=initialStart,endEpoch=initialEnd,sha256=hashlib.sha256((out/'launch-initial.png').read_bytes()).hexdigest()),indent=2)+'\n')
 while time.monotonic()<deadline:
  rs=readrows();observed=time.time()
  for r in rs:
   if r['sequence'] in known:continue
   known.add(r['sequence'])
   if r['event']!='highlight-after' or r.get('cachedIDs')!=['edge-20-left','edge-20-right']:continue
   if scene is None:
    earlierClear=[q for q in rs if q['sequence']<r['sequence'] and q.get('sceneLifecycleToken')==r['sceneLifecycleToken'] and q['event']=='highlight-after' and q.get('cachedIDs')==[]]
    if not earlierClear:
     with (out/'excluded-prestart-candidates.jsonl').open('a') as f:f.write(json.dumps(dict(record=r,reason='No preceding empty/countdown selection on this scene; not labeled running Hang'))+'\n')
     continue
    scene=r['sceneLifecycleToken']
   if r['sceneLifecycleToken']!=scene:continue
   if len(transitions)>=3:continue
   expected=['active','preview','active'][len(transitions)]
   assert r['cachedMode']==expected,('Unexpected phase',r)
   i=len(transitions);transitions.append({'phaseIndex':i,'mode':expected,'actualMutation':r,'hostFirstObservedEpoch':observed,'observationLagSeconds':observed-r['epoch']})
   for offset in [.25,1,3,5]:pending.append({'phaseIndex':i,'mode':expected,'offset':offset,'targetEpoch':r['epoch']+offset})
   (out/'transition-observations.json').write_text(json.dumps(transitions,indent=2)+'\n')
  now=time.time();pending.sort(key=lambda q:q['targetEpoch'])
  if pending and pending[0]['targetEpoch']<=now:
   q=pending.pop(0);name=f"phase-{q['phaseIndex']}-{q['mode']}-plus-{q['offset']:g}.png"
   beforeRows=readrows();beforeObserved=time.time();captureStart=time.time();run('xcrun','simctl','io',uid,'screenshot',out/name);captureEnd=time.time();afterRows=readrows();afterObserved=time.time()
   row=dict(q,path=str(out/name),sha256=hashlib.sha256((out/name).read_bytes()).hexdigest(),startEpoch=captureStart,endEpoch=captureEnd,startDelayFromTarget=captureStart-q['targetEpoch'],traceReadBefore={'observedEpoch':beforeObserved,'lastSequence':beforeRows[-1]['sequence'] if beforeRows else None},traceReadAfter={'observedEpoch':afterObserved,'lastSequence':afterRows[-1]['sequence'] if afterRows else None})
   captures.append(row);(out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
  if len(transitions)==3 and len(captures)==12:
   tail=[r for r in rs if r['event']=='highlight-before' and r.get('sceneLifecycleToken')==scene and r.get('cachedMode')=='active' and r.get('requestedMode')=='preview' and r['epoch']>transitions[2]['actualMutation']['epoch']]
   if tail and time.time()>tail[-1]['epoch']+.5:
    (out/'following-preview-tail.json').write_text(json.dumps(dict(record=tail[-1],hostObservedEpoch=time.time()),indent=2)+'\n');break
  time.sleep(.03)
 assert len(transitions)==3 and len(captures)==12 and (out/'following-preview-tail.json').exists(),'Hard bound reached before all required transitions/captures/following-preview tail'
 save_trace();print(json.dumps({'phases':len(transitions),'captures':len(captures),'elapsedSeconds':time.monotonic()-start,'run':str(out)}))
except Exception:
 (out/'failure.txt').write_text(traceback.format_exc());save_trace();raise
finally:
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
