from pathlib import Path
import os,sys,json,time,subprocess,hashlib,traceback,signal,atexit,re,shlex
import branch_schema as schema
import muted_audio_schema as audio_schema
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
releasePath=Path(sys.argv[1]);release=json.loads(releasePath.read_text());role=release['role'];assert role in ['live','image'];arm=release['arm']
assert re.fullmatch(r'hand-image-muted-workout-(live|image)-[a-z0-9-]+',arm) and arm.startswith('hand-image-muted-workout-'+role+'-')
assert release['runtimeAuthorized'] is True and release['rootSourceRuntimeRelease'] is True
assert release['owner']=='placid-badger-cad-second-half' and release['retainedDetachIntervention'] is False
assert release['helperSHA256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
assert release['schemaSHA256']==hashlib.sha256(Path(schema.__file__).read_bytes()).hexdigest()
assert release['eventSchemaSHA256']==hashlib.sha256(Path(__file__).with_name('event-schema.json').read_bytes()).hexdigest()
assert release['audioMuted'] is True
assert release['appArguments']==['-workoutAudioCuesEnabled','NO']
assert release['audioSchemaSHA256']==hashlib.sha256(Path(audio_schema.__file__).read_bytes()).hexdigest()
assert release['markerSchemaSHA256']==hashlib.sha256(Path(__file__).with_name('marker-schema.json').read_bytes()).hexdigest()
assert re.fullmatch(r'[a-f0-9]{64}',release['binarySHA256'])
assert release['simulatorUUID']=='BDCA0D77-94C2-4A97-900B-443F75C64691'
assert release['controllerPID']==96137
assert release['fixedCueReviewRequired'] is True and release['staticFeasibilityApproved'] is True
assert release['staticDarkBackingApproved'] is True
assert release['expectedFixedCue']=='halfCrimp/index,middle,ring,pinky/pair'
assert release['commonValidatorsRequired'] is True and release['visualReviewRequired'] is True
for prefix in ['codePackageParity','priorFrozenManifest']:
 path=Path(release[prefix+'Path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==release[prefix+'SHA256'];value=json.loads(raw)
 if prefix=='codePackageParity':
  assert value['allEqual'] and len(value['checks'])==27 and all(x['equal'] for x in value['checks'])
  for proof in value['checks']:assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
  assert any(x.get('category')=='installedMachO' and x.get('sha256')==release['binarySHA256'] for x in value['checks'])
 else:
  for proof in value['files']:assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
assert release['sourceAndPackageFiles']
assert release['routineSource']['path']=='HangTen/Resources/PlanLibrary.json'
assert hashlib.sha256(Path(release['routineSource']['path']).read_bytes()).hexdigest()==release['routineSource']['sha256']
for proof in release['sourceAndPackageFiles']:
 assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
if role=='image':
 gatePath=Path(release['completedControlAuditPath']);raw=gatePath.read_bytes();assert hashlib.sha256(raw).hexdigest()==release['completedControlAuditSHA256'];gate=json.loads(raw)
 assert gate['binarySHA256']==release['binarySHA256'] and gate['role']=='live'
 assert gate['audioMuted'] is True and gate['appArguments']==release['appArguments']
 assert gate['arm']=='hand-image-muted-workout-live-b', 'Only fresh muted control may authorize this image arm'
 assert gate['validCompleteControl'] is True and gate['visualResult']=='FAIL' and gate['imageAuthorized'] is True
 assert gate['all12WholeImagesReviewed'] and gate['commonValidatorsPassed'] and gate['branchChecksPassed']
 for proof in gate['frozenControlFiles']:assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
out=base/(arm+'-landscape');out.mkdir(exist_ok=False);(out/'runtime-release.json').write_bytes(releasePath.read_bytes())
uid=release['simulatorUUID'];commands=[];captures=[];transitions=[];tracefolder=None;active=None;appearance=None;appearanceObserved=None;pending=[];known=set();scene=None;observations=[];observedSequences=set()
start=time.monotonic();deadline=start+300;captureTolerance=.150
app_pid=None;launch_attempted=False;failure=None;postflight_errors=[]

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
 schema.protocol(rows,role)
 audio_schema.validate(rows)
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

def run(*args,env=None,captureTarget=None,cleanup=False,limit=20,allow_failure=False):
 global active
 cmd=['rtk','proxy',*map(str,args)];n=len(commands)
 row=dict(command=cmd,startEpoch=time.time(),startMonotonic=time.monotonic(),owner='placid-badger-cad-second-half',commandLimitSeconds=limit)
 if not cleanup:assert remaining()>0,'Overall300s deadline reached before command start'
 commands.append(row);write('commands.json',commands)
 row['startEpoch']=time.time();row['startMonotonic']=time.monotonic()
 if captureTarget is not None and row['startEpoch']-captureTarget>captureTolerance:
  row.update(endEpoch=time.time(),notLaunched=True,missedCapture=True);write('commands.json',commands)
  write('missed-capture.json',dict(targetEpoch=captureTarget,observedEpoch=row['startEpoch'],toleranceSeconds=captureTolerance,backfilled=False))
  raise AssertionError('Capture deadline missed before Popen')
 stdout=out/f'{n:03d}-stdout.txt';stderr=out/f'{n:03d}-stderr.txt'
 with stdout.open('xb') as a,stderr.open('xb') as b:
  active=subprocess.Popen(cmd,stdout=a,stderr=b,env=env)
  row.update(pid=active.pid,parentPID=os.getpid());write('commands.json',commands)
  commandDeadline=row['startMonotonic']+limit
  try:
   while active.poll() is None:
    if not cleanup:observe()
    if time.monotonic()>=commandDeadline or (not cleanup and time.monotonic()>=deadline):
     row.update(timeout=True,rightCensored=True);raise TimeoutError('Command/overall deadline')
    time.sleep(.015)
   row['exitStatus']=active.returncode
  except BaseException:
   row['interruptedOrFailed']=True;raise
  finally:
   stop_owned(active);row.update(exitStatus=active.returncode,endEpoch=time.time(),endMonotonic=time.monotonic());active=None;write('commands.json',commands)
 if row['exitStatus'] and not allow_failure:raise subprocess.CalledProcessError(row['exitStatus'],cmd)
 return stdout.read_text().strip()

def save_trace():
 copies=[];rs=[]
 if tracefolder:
  for f in tracefolder.glob('events-*.jsonl'):
   raw=f.read_bytes();t=out/f.name;t.write_bytes(raw);copies.append({'source':str(f),'copy':str(t),'sha256':hashlib.sha256(raw).hexdigest()});rs.extend(json.loads(l) for l in raw.splitlines(keepends=True) if l.endswith(b'\n'))
 complete=bool(rs) and all(r['complete'] for r in rs) and [r['sequence'] for r in rs]==list(range(1,len(rs)+1)) and all((out/Path(c['copy']).name).read_bytes().endswith(b'\n') for c in copies)
 (out/'trace-copy.json').write_text(json.dumps({'copies':copies,'records':len(rs),'completeContiguous':complete,'copiedEpoch':time.time(),'includesSamplerEnd':any(r['event']=='sample-end' for r in rs)},indent=2)+'\n')

def interrupted(signum,frame):raise InterruptedError('Signal '+str(signum))
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
def exit_cleanup():
 if active is not None:stop_owned(active)
atexit.register(exit_cleanup)

try:
 lifecycle=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/prep/lifecycle.zsh')
 controller=run('ps','-p',str(release['controllerPID']),'-o','pid=,command=')
 tokens=shlex.split(controller);assert tokens and int(tokens[0])==release['controllerPID']
 assert str(lifecycle) in tokens[1:] or str(lifecycle.resolve()) in tokens[1:]
 assert not Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/ios-diagnosis/cleanup-requested').exists()
 registration=Path('.context/paseo-owned-simulators').read_text();assert uid in registration
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
 if role=='image':flags['HANGTEN_REVIEW_HAND_IMAGE']='1'
 flags['HANGTEN_REVIEW_STARTUP_OBSERVATION']='1'
 # Prospective release gate chooses common intervention mode; no default inference.
 retentionExpected=release['retainedDetachIntervention']
 assert isinstance(retentionExpected,bool)
 assert retentionExpected is False
 flags['HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT']='1'
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')};env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()})
 (out/'launch-review-environment.json').write_text(json.dumps(flags,indent=2)+'\n')
 write('protocol.json',dict(hardBoundSeconds=300,role=role,plannedPhases=['active','preview','active'],captureOffsetsAfterActualMutation=[.25,1,3,5],captureStartToleranceSeconds=captureTolerance,missedCapturePolicy='Record missed window and stop; never backfill',initialDiscoveryBoundSecondsAfterRecordedAppearance=30,methodDifference='External polling continues during the unchanged initial screenshot command',afterLaunchUIAccess='screenshots only; no AX/touches/Skip',routineUnchanged=True,branchContract='Live attached pair versus current image publication; no capture delay for hand readiness',semanticLimit=schema.LIMITS))
 tracefolder=data/'Documents'/('HighlightDiagnostic-'+flags['HANGTEN_REVIEW_DIAGNOSTIC_RUN']);assert not tracefolder.exists()
 write('launch-app-arguments.json',dict(audioMuted=True,appArguments=release['appArguments'],scope='Separate supported muted workflow; not an audio-enabled transfer. Argument-domain override only.'))
 launch_attempted=True
 launch=run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',*release['appArguments'],env=env)
 match=re.search(r':\s*(\d+)\s*$',launch);app_pid=int(match.group(1)) if match else None
 write('app-registration.json',dict(simulatorUUID=uid,pid=app_pid,bundle='com.hangten.training',owner=release['owner']))
 assert app_pid is not None,'Missing exact launched app PID'
 # New shared startup protocol: observe existing events only; no AX/touch or UI write.
 readinessStart=time.monotonic();readinessStartEpoch=time.time();readinessDeadline=min(deadline,readinessStart+20);ready=None
 while time.monotonic()<readinessDeadline:
  readinessRows=observe()
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
   beforeRows=readrows();beforeObserved=time.time();branchBefore=None;branchError=None
   try:branchBefore=schema.capture_checkpoint(beforeRows,role,allow_first_before_gap=q['phaseIndex']==0 and q['offset']==.25,capture_start=time.time())
   except Exception:branchError=traceback.format_exc()
   captureStart=time.time()
   if captureStart-q['targetEpoch']>captureTolerance:
    write('missed-capture.json',dict(q,observedEpoch=captureStart,latenessSeconds=captureStart-q['targetEpoch'],toleranceSeconds=captureTolerance,backfilled=False));raise AssertionError('Capture start deadline missed')
   run('xcrun','simctl','io',uid,'screenshot',out/name,captureTarget=q['targetEpoch']);captureStart=commands[-1]['startEpoch'];captureEnd=commands[-1]['endEpoch'];afterRows=readrows();afterObserved=time.time()
   row=dict(q,path=str(out/name),sha256=hashlib.sha256((out/name).read_bytes()).hexdigest(),startEpoch=captureStart,endEpoch=captureEnd,startDelayFromTarget=captureStart-q['targetEpoch'],traceReadBefore={'observedEpoch':beforeObserved,'lastSequence':beforeRows[-1]['sequence'] if beforeRows else None},traceReadAfter={'observedEpoch':afterObserved,'lastSequence':afterRows[-1]['sequence'] if afterRows else None})
   if branchBefore and branchBefore.get('observationStatus')=='PENDING_FIRST_BEFORE_CENSUS_GAP':
    assert all(branchBefore[k]['epoch']<captureStart for k in ('constructor','make','fit'))
    branchBefore['actualCaptureStartEpoch']=captureStart
   row['branchBefore']=branchBefore;row['branchBeforeError']=branchError
   captures.append(row);(out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
   if branchError:raise AssertionError('Required hand readiness missing at mandatory checkpoint; screenshot retained without waiting: '+branchError)
   try:row['branchAfter']=schema.capture_checkpoint(afterRows,role,allow_first_before_gap=q['phaseIndex']==0 and q['offset']==.25,capture_start=captureStart)
   except Exception:
    row['branchAfterError']=traceback.format_exc();write('captures.json',captures);raise
   if role=='image':assert [(branchBefore['publication'][k],row['branchAfter']['publication'][k]) for k in ('sessionID','revision')] == [(branchBefore['publication'][k],branchBefore['publication'][k]) for k in ('sessionID','revision')],'Publication changed during mandatory screenshot'
   (out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
  if len(transitions)==3 and len(captures)==12:
   tail=[r for r in rs if r['event']=='highlight-before' and r.get('sceneLifecycleToken')==scene and r.get('cachedMode')=='active' and r.get('requestedMode')=='preview' and r['epoch']>transitions[2]['actualMutation']['epoch']]
   if tail and time.time()>tail[-1]['epoch']+.5:
    (out/'following-preview-tail.json').write_text(json.dumps(dict(record=tail[-1],hostObservedEpoch=time.time()),indent=2)+'\n');break
  time.sleep(.03)
 assert len(transitions)==3 and len(captures)==12 and (out/'following-preview-tail.json').exists(),'Hard bound reached before all required transitions/captures/following-preview tail'
 write('muted-audio-validation.json',audio_schema.validate(readrows(),final=True))
 save_trace();print(json.dumps({'phases':len(transitions),'captures':len(captures),'elapsedSeconds':time.monotonic()-start,'run':str(out)}))
except BaseException:
 failure=traceback.format_exc();(out/'failure.txt').write_text(failure)
finally:
 if active is not None:stop_owned(active)
 cleanup=dict(scope='Exact launched app only; existing controller retains Simulator/DD')
 if launch_attempted:
  try:
   run('xcrun','simctl','terminate',uid,'com.hangten.training',cleanup=True,limit=10,allow_failure=True)
   if app_pid:
    ps=run('ps','-p',str(app_pid),'-o','pid=,comm=',cleanup=True,limit=3,allow_failure=True)
    cleanup['recordedAppPIDAbsent']=commands[-1]['exitStatus']==1 and not ps.strip()
   else:cleanup['recordedAppPIDAbsent']=False
  except BaseException:cleanup['error']=traceback.format_exc()
 cleanup['passed']=(not launch_attempted or cleanup.get('recordedAppPIDAbsent') is True) and 'error' not in cleanup
 write('app-cleanup.json',cleanup)
 if not cleanup['passed']:postflight_errors.append('Exact app cleanup not verified')
 try:save_trace()
 except BaseException:
  (out/'trace-retention-error.txt').write_text(traceback.format_exc());postflight_errors.append('Trace retention failed')
 try:write('muted-audio-final-snapshot-validation.json',audio_schema.validate(readrows(),final=failure is None))
 except BaseException:
  postflight_errors.append('Muted audio scalar gate failed');(out/'muted-audio-validation-error.txt').write_text(traceback.format_exc())
 artifactCopies=[]
 try:artifacts=schema.published_artifacts(readrows())
 except BaseException:
  artifacts=[];postflight_errors.append('Published metadata extraction failed');(out/'artifact-extraction-error.txt').write_text(traceback.format_exc())
 for artifact in artifacts:
  record=dict(published=artifact,copied=False)
  try:
   p=Path(artifact['path']);assert p.resolve().is_relative_to(tracefolder.resolve()) and p.suffix.lower()=='.png'
   assert re.fullmatch(r'[A-Fa-f0-9-]{36}',artifact['sessionID']) and isinstance(artifact['revision'],int) and artifact['revision']>0
   target=out/'published-artifacts'/artifact['sessionID']/('revision-'+str(artifact['revision'])+'.png');target.parent.mkdir(parents=True,exist_ok=True)
   raw=p.read_bytes()
   with target.open('xb') as f:f.write(raw)
   record.update(copied=True,destination=str(target.relative_to(out)),actualSHA256=hashlib.sha256(raw).hexdigest(),actualBytes=len(raw))
   record['matchesPublishedMetadata']=record['actualSHA256']==artifact['sha256'] and len(raw)==artifact['bytes']
   if not record['matchesPublishedMetadata']:postflight_errors.append('PNG metadata mismatch; actual bytes preserved')
  except BaseException:record['error']=traceback.format_exc();postflight_errors.append('PNG retention failed')
  artifactCopies.append(record)
 write('all-published-artifact-copies.json',artifactCopies)
 try:
  for proof in release['sourceAndPackageFiles']+[release['routineSource']]:assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
  for proof in json.loads(Path(release['codePackageParityPath']).read_text())['checks']:assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
 except BaseException:postflight_errors.append('Frozen source/package changed');(out/'postflight-parity-error.txt').write_text(traceback.format_exc())
 write('startup-marker-observations.json',observations);write('captures.json',captures);write('commands.json',commands)
 write('completion.json',dict(captureProtocolCompleted=failure is None and not postflight_errors,visualResult='NOT_REVIEWED',commonValidators='PENDING_SEPARATE_REVIEW',overallComparisonPassed=False,postflightErrors=postflight_errors,limits=schema.LIMITS))
if failure or postflight_errors:raise SystemExit(1)
