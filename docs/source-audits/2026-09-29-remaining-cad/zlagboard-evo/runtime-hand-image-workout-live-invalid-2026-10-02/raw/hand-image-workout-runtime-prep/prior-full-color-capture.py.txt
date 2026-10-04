from pathlib import Path
import os,sys,json,time,subprocess,hashlib,traceback,signal,atexit
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
releasePath=Path(sys.argv[1]);release=json.loads(releasePath.read_text());role=release['role'];assert role in ['control','action'];arm='startup-full-color-'+role
assert release['runtimeAuthorized'] is True and release['arm']==arm
assert release['rootSourceRuntimeRelease'] is True and release['retainedDetachIntervention'] is False
assert release['helperSHA256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
assert release['binarySHA256']=='09310b53114826e1e9c39a499846b2e57a6b464e576aa7bf879b56709d267854'
assert release['simulatorUUID']=='BDCA0D77-94C2-4A97-900B-443F75C64691'
for prefix in ['codePackageParity','priorFrozenManifest']:
 path=Path(release[prefix+'Path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==release[prefix+'SHA256'];value=json.loads(raw)
 if prefix=='codePackageParity':
  assert value['allEqual'] and len(value['checks'])==27 and all(x['equal'] for x in value['checks'])
  assert any(x.get('category')=='installedMachO' and x.get('sha256')==release['binarySHA256'] for x in value['checks'])
 else:
  for proof in value['files']:assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
if role=='action':
 gatePath=Path(release['completedControlAuditPath']);raw=gatePath.read_bytes();assert hashlib.sha256(raw).hexdigest()==release['completedControlAuditSHA256'];gate=json.loads(raw)
 assert gate['binarySHA256']==release['binarySHA256'] and gate['validCompleteControl'] is True and gate['visualResult']=='FAIL' and gate['actionAuthorized'] is True
 assert gate['originalValidatorStatusRetained'] is True and gate['supplementalTimingCriterionPassed'] is True
out=base/(arm+'-landscape');out.mkdir(exist_ok=False);(out/'runtime-release.json').write_bytes(releasePath.read_bytes())
uid=release['simulatorUUID'];commands=[];captures=[];transitions=[];tracefolder=None;active=None;appearance=None;appearanceObserved=None;pending=[];known=set();scene=None;observations=[];observedSequences=set()
start=time.monotonic();deadline=start+300;captureTolerance=.150

def write(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')

def readrows():
 rows=[]
 if tracefolder:
  for f in sorted(tracefolder.glob('events-*.jsonl')):
   for line in f.read_bytes().splitlines(keepends=True):
    if line.endswith(b'\n'):rows.append(json.loads(line))
 return rows

def observe():
 global appearance,appearanceObserved
 rows=readrows();now=time.time()
 for r in rows:
  if r['sequence'] not in observedSequences:
   observedSequences.add(r['sequence'])
   if r['event'].startswith('startup-') or r['event']=='workout-probe-appear-before-autostart':observations.append(dict(sequence=r['sequence'],event=r['event'],epoch=r['epoch'],hostFirstObservedEpoch=now))
  if r['event']=='workout-probe-appear-before-autostart' and appearance is None:
   appearance=r;appearanceObserved=now;write('appearance-anchor.json',dict(record=r,firstObservedEpoch=now))
 return rows

def remaining():
 observe();return deadline-time.monotonic()
def stop_owned(proc):
 # Only this owned, still-unreaped direct Popen child; no process-group/shared-service action.
 if proc.poll() is None:
  proc.terminate()
  try:proc.wait(timeout=.5)
  except subprocess.TimeoutExpired:
   proc.kill();proc.wait(timeout=1)

def drain_bounded(proc,row):
 try:return proc.communicate(timeout=1)
 except subprocess.TimeoutExpired as exc:
  row['pipeDrainRightCensored']=True
  # Preserve available bytes; never wait indefinitely for inherited pipe holders.
  for stream in [proc.stdout,proc.stderr]:
   if stream is not None:stream.close()
  return exc.stdout or b'',exc.stderr or b''

def run(*args,env=None,captureTarget=None):
 global active
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);row=dict(command=cmd,startEpoch=time.time(),startMonotonic=time.monotonic(),owner='placid-badger-cad-second-half-startup-observation',commandLimitSeconds=20)
 assert remaining()>0,'Observation/setup deadline reached before command start'
 commands.append(row);write('commands.json',commands)
 row['requestedEpoch']=row['startEpoch'];row['startEpoch']=time.time();row['startMonotonic']=time.monotonic()
 if captureTarget is not None and row['startEpoch']-captureTarget>captureTolerance:
  row.update(endEpoch=time.time(),endMonotonic=time.monotonic(),notLaunched=True,missedCapture=True)
  write('missed-capture.json',dict(targetEpoch=captureTarget,observedEpoch=row['startEpoch'],toleranceSeconds=captureTolerance,backfilled=False));write('commands.json',commands);raise AssertionError('Capture deadline missed before Popen')
 active=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 row.update(pid=active.pid,parentPID=os.getpid());write('commands.json',commands)
 commandDeadline=row['startMonotonic']+20
 stdout=stderr=None
 try:
  while True:
   left=min(commandDeadline-time.monotonic(),remaining())
   if left<=0:
    row.update(timeout=True,rightCensored=True,timeoutReason='overall300s-deadline' if remaining()<=0 else 'command20s')
    stop_owned(active);stdout,stderr=drain_bounded(active,row);break
   try:
    stdout,stderr=active.communicate(timeout=min(.03,left));break
   except subprocess.TimeoutExpired:pass
  row.update(endEpoch=time.time(),endMonotonic=time.monotonic(),exitStatus=active.returncode,timeout=row.get('timeout',False))
  (out/f'{n:03d}-stdout.txt').write_bytes(stdout);(out/f'{n:03d}-stderr.txt').write_bytes(stderr)
  observe()
  row['endedAfterOverallDeadline']=row['endMonotonic']>deadline
  write('commands.json',commands)
  if row['timeout']:raise TimeoutError(row['timeoutReason'])
  if active.returncode:raise subprocess.CalledProcessError(active.returncode,cmd,stdout,stderr)
  return stdout.decode().strip()
 finally:
  stop_owned(active)
  if stdout is None:
   stdout,stderr=drain_bounded(active,row)
   (out/f'{n:03d}-stdout.txt').write_bytes(stdout);(out/f'{n:03d}-stderr.txt').write_bytes(stderr)
   row.update(endEpoch=time.time(),endMonotonic=time.monotonic(),exitStatus=active.returncode,rightCensored=True,interrupted=True)
   write('commands.json',commands)
  active=None

def save_trace():
 copies=[];rs=[]
 if tracefolder:
  for f in tracefolder.glob('events-*.jsonl'):
   raw=f.read_bytes();t=out/f.name;t.write_bytes(raw);copies.append({'source':str(f),'copy':str(t),'sha256':hashlib.sha256(raw).hexdigest()});assert raw.endswith(b'\n');rs.extend(json.loads(l) for l in raw.splitlines())
 if rs:assert all(r['complete'] for r in rs) and [r['sequence'] for r in rs]==list(range(1,len(rs)+1))
 (out/'trace-copy.json').write_text(json.dumps({'copies':copies,'records':len(rs),'completeContiguous':bool(rs),'copiedEpoch':time.time(),'includesSamplerEnd':any(r['event']=='sample-end' for r in rs)},indent=2)+'\n')

def interrupted(signum,frame):raise InterruptedError('Signal '+str(signum))
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
def exit_cleanup():
 if active is not None:stop_owned(active)
atexit.register(exit_cleanup)

try:
 app=Path(run('xcrun','simctl','get_app_container',uid,'com.hangten.training','app'))
 binary=app/'HangTen.debug.dylib'
 actualBinarySHA=hashlib.sha256(binary.read_bytes()).hexdigest()
 (out/'installed-binary-gate.json').write_text(json.dumps({'path':str(binary),'sha256':actualBinarySHA,'expected':release['binarySHA256']},indent=2)+'\n')
 assert actualBinarySHA==release['binarySHA256'],'Installed binary mismatch; no launch permitted'
 data=Path(run('xcrun','simctl','get_app_container',uid,'com.hangten.training','data'))
 flags={'HANGTEN_REVIEW_BOARD_ID':'zlagboard.evo','HANGTEN_REVIEW_PLAN_ID':'research.max-hangs','HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC':'1','HANGTEN_REVIEW_DIAGNOSTIC_RUN':'placid-badger-cad-second-half-'+arm,'HANGTEN_REVIEW_LANDSCAPE':'1','HANGTEN_REVIEW_WORKOUT_BOUNDARY_CENSUS':'1'}
 flags['HANGTEN_REVIEW_PREDECESSOR_ATTACHMENT_CENSUS']='1'
 flags['HANGTEN_REVIEW_BOARD_HOST_OBSERVATION']='1'
 flags['HANGTEN_REVIEW_HAND_LIFETIME_CENSUS']='1'
 flags['HANGTEN_REVIEW_SYNC_DELIVERY_COUNTERS']='1'
 if role=='action':flags['HANGTEN_REVIEW_SUPPRESS_PRESTART_HAND_HOSTS']='1'
 flags['HANGTEN_REVIEW_STARTUP_OBSERVATION']='1'
 # Prospective release gate chooses common intervention mode; no default inference.
 retentionExpected=release['retainedDetachIntervention']
 assert isinstance(retentionExpected,bool)
 if retentionExpected:flags['HANGTEN_REVIEW_BOARD_DETACH_TRIAL']='1'
 if retentionExpected:flags['HANGTEN_REVIEW_DETACH_DISAPPEARING_BOARD_HOST']='1'
 flags['HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT']='1'
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')};env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()})
 (out/'launch-review-environment.json').write_text(json.dumps(flags,indent=2)+'\n')
 write('protocol.json',dict(hardBoundSeconds=300,role=role,plannedPhases=['active','preview','active'],captureOffsetsAfterActualMutation=[.25,1,3,5],captureStartToleranceSeconds=captureTolerance,missedCapturePolicy='Record missed window and stop; never backfill',initialDiscoveryBoundSecondsAfterRecordedAppearance=30,methodDifference='External polling continues during the unchanged initial screenshot command',afterLaunchUIAccess='screenshots only; no AX/touches/Skip',routineUnchanged=True,supplementalHandTiming='Unchanged after-last-positive and before actual first screenshot START; no relaxation for delayed hands'))
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
    if make and r['sequence']>=make['sequence'] and h['trainMarked'] and h['currentOwner'] and h['modelAlive'] and h['modelRetainedForTrial']==retentionExpected and h['attachmentObserved'] and not h['disappeared'] and not h['detached'] and h['invalid']=='nil' and attached and living:
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
  rs=observe();observed=time.time()
  if not transitions and appearance is not None and observed>appearance['epoch']+30:
   write('missing-initial-sequence.json',dict(reason='No eligible firstHang within30s of recorded appearance',appearance=appearance,observedEpoch=observed));raise AssertionError('Missing initial sequence; stop without retry')
  for r in rs:
   if r['sequence'] in known:continue
   known.add(r['sequence'])
   if r['event']!='highlight-after' or r.get('cachedIDs')!=['edge-20-left','edge-20-right']:continue
   if scene is None:
    earlierClear=[q for q in rs if q['sequence']<r['sequence'] and q.get('sceneLifecycleToken')==r['sceneLifecycleToken'] and q['event']=='highlight-after' and q.get('cachedIDs')==[]]
    if not earlierClear:
     with (out/'excluded-prestart-candidates.jsonl').open('a') as f:f.write(json.dumps(dict(record=r,reason='No preceding empty/countdown selection on this scene; not labeled running Hang'))+'\n')
     if r['cachedMode']=='preview':
      write('missing-initial-sequence.json',dict(reason='Preview reached without preceding empty/firstHang sequence',record=r));raise AssertionError('Missing initial sequence before Rest; stop')
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
   beforeRows=readrows();beforeObserved=time.time();captureStart=time.time()
   if captureStart-q['targetEpoch']>captureTolerance:
    write('missed-capture.json',dict(q,observedEpoch=captureStart,latenessSeconds=captureStart-q['targetEpoch'],toleranceSeconds=captureTolerance,backfilled=False));raise AssertionError('Capture start deadline missed')
   run('xcrun','simctl','io',uid,'screenshot',out/name,captureTarget=q['targetEpoch']);captureStart=commands[-1]['startEpoch'];captureEnd=commands[-1]['endEpoch'];afterRows=readrows();afterObserved=time.time()
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
 if active is not None:stop_owned(active)
 write('startup-marker-observations.json',observations)
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
