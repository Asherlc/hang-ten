from pathlib import Path
import os,sys,json,time,subprocess,hashlib,traceback,signal,atexit
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
arm='startup-observation-action'
releasePath=Path(sys.argv[1]);release=json.loads(releasePath.read_text())
assert release['runtimeAuthorized'] is True and release['arm']==arm
assert release['oneStartupObservationAuthorized'] is True
assert release['helperSHA256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
assert release['rootSourceRuntimeRelease'] is True
assert release['retainedDetachIntervention'] is False
assert release['simulatorUUID']=='BDCA0D77-94C2-4A97-900B-443F75C64691'
assert release['startupMarkerSchemaReviewed'] is True
assert release['markerSchema']['reviewed'] is True and release['markerSchema']['events']
assert hashlib.sha256(Path(release['priorActionEnvironmentPath']).read_bytes()).hexdigest()==release['priorActionEnvironmentSHA256']
assert release['binarySHA256']!='f98a07f4383af14396d8442581a330f4d3523d0c9854436420b67bf14b681d97'
for prefix in ['codePackageParity','priorFrozenManifest','sourceFreeze']:
 p=Path(release[prefix+'Path']);raw=p.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==release[prefix+'SHA256']
 value=json.loads(raw)
 if prefix=='codePackageParity':
  assert value['allEqual'] and len(value['checks'])==27 and all(x['equal'] for x in value['checks'])
  assert any(x.get('category')=='installedMachO' and x.get('sha256')==release['binarySHA256'] for x in value['checks'])
 else:
  for proof in value['files']:assert hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest()==proof['sha256']
out=base/'startup-observation-action-landscape';out.mkdir(exist_ok=False)
(out/'runtime-release.json').write_bytes(releasePath.read_bytes())
uid=release['simulatorUUID'];commands=[];tracefolder=None;active=None;appearance=None;appearanceObserved=None;appearanceDeadline=None;windowDeadline=None;openURLStart=None;seen=set();observations=[]
start=time.monotonic();setupDeadline=start+90;windowEnd=None

def write(name,value):
 (out/name).write_text(json.dumps(value,indent=2)+'\n')

def readrows():
 rows=[]
 if tracefolder:
  for f in sorted(tracefolder.glob('events-*.jsonl')):
   for line in f.read_bytes().splitlines(keepends=True):
    if line.endswith(b'\n'):rows.append(json.loads(line))
 return rows

def observe():
 global appearance,appearanceObserved,windowDeadline
 rows=readrows();now=time.time();mono=time.monotonic()
 for r in rows:
  if r['sequence'] not in seen:
   seen.add(r['sequence'])
   if r['event']=='workout-probe-appear-before-autostart' or r['event'] in release['markerSchema']['events']:
    observations.append(dict(sequence=r['sequence'],event=r['event'],recordEpoch=r['epoch'],firstObservedEpoch=now,firstObservedMonotonic=mono))
  if r['event']=='workout-probe-appear-before-autostart' and appearance is None and openURLStart is not None:
   assert r['epoch']>=openURLStart,'Unexpected pre-openurl appearance'
   appearance=r;appearanceObserved=dict(epoch=now,monotonic=mono)
   # Convert the event wall-clock deadline once; never reset after screenshot or late delivery.
   windowDeadline=mono+(r['epoch']+30-now)
   write('appearance-anchor.json',dict(record=r,firstObserved=appearanceObserved,endEpoch=r['epoch']+30,endMonotonic=windowDeadline,observedAfterArrivalDeadline=mono>appearanceDeadline))
 return rows

def remaining():
 if openURLStart is None:return setupDeadline-time.monotonic()
 observe()
 return (windowDeadline if appearance is not None else appearanceDeadline)-time.monotonic()

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

def run(*args,env=None):
 global active
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);row=dict(command=cmd,startEpoch=time.time(),startMonotonic=time.monotonic(),owner='placid-badger-cad-second-half-startup-observation',commandLimitSeconds=20)
 assert remaining()>0,'Observation/setup deadline reached before command start'
 commands.append(row);write('commands.json',commands)
 active=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 row.update(pid=active.pid,parentPID=os.getpid());write('commands.json',commands)
 commandDeadline=row['startMonotonic']+20
 stdout=stderr=None
 try:
  while True:
   left=min(commandDeadline-time.monotonic(),remaining())
   if left<=0:
    row.update(timeout=True,rightCensored=True,timeoutReason='observation-or-appearance-deadline' if remaining()<=0 else 'command20s')
    stop_owned(active);stdout,stderr=drain_bounded(active,row);break
   try:
    stdout,stderr=active.communicate(timeout=min(.03,left));break
   except subprocess.TimeoutExpired:pass
  row.update(endEpoch=time.time(),endMonotonic=time.monotonic(),exitStatus=active.returncode,timeout=row.get('timeout',False))
  (out/f'{n:03d}-stdout.txt').write_bytes(stdout);(out/f'{n:03d}-stderr.txt').write_bytes(stderr)
  observe()
  row['endedAfterObservationWindow']=windowDeadline is not None and row['endMonotonic']>windowDeadline
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
 copies=[];rows=[]
 if tracefolder:
  for f in sorted(tracefolder.glob('events-*.jsonl')):
   raw=f.read_bytes();(out/f.name).write_bytes(raw);complete=raw.endswith(b'\n');copies.append(dict(source=str(f),copy=str(out/f.name),sha256=hashlib.sha256(raw).hexdigest(),endsWithNewline=complete))
   rows.extend(json.loads(l) for l in raw.splitlines(keepends=True) if l.endswith(b'\n'))
 write('trace-copy.json',dict(copies=copies,records=len(rows),completeContiguous=bool(rows) and all(x['endsWithNewline'] for x in copies) and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)),copiedEpoch=time.time(),scope='Raw file copy can include a short cleanup/final-copy tail after the fixed observation endpoint; classify records by epoch, never extend the window.'))
 write('marker-first-observations.json',observations)

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
 flags={'HANGTEN_REVIEW_BOARD_ID':'zlagboard.evo','HANGTEN_REVIEW_PLAN_ID':'research.max-hangs','HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC':'1','HANGTEN_REVIEW_DIAGNOSTIC_RUN':'placid-badger-cad-second-half-startup-observation-action','HANGTEN_REVIEW_LANDSCAPE':'1','HANGTEN_REVIEW_WORKOUT_BOUNDARY_CENSUS':'1'}
 flags['HANGTEN_REVIEW_PREDECESSOR_ATTACHMENT_CENSUS']='1'
 flags['HANGTEN_REVIEW_BOARD_HOST_OBSERVATION']='1'
 flags['HANGTEN_REVIEW_HAND_LIFETIME_CENSUS']='1'
 flags['HANGTEN_REVIEW_SYNC_DELIVERY_COUNTERS']='1'
 flags['HANGTEN_REVIEW_SUPPRESS_PRESTART_HAND_HOSTS']='1'
 flags['HANGTEN_REVIEW_STARTUP_OBSERVATION']='1'
 # Prospective release gate chooses common intervention mode; no default inference.
 retentionExpected=release['retainedDetachIntervention']
 assert isinstance(retentionExpected,bool)
 if retentionExpected:flags['HANGTEN_REVIEW_BOARD_DETACH_TRIAL']='1'
 if retentionExpected:flags['HANGTEN_REVIEW_DETACH_DISAPPEARING_BOARD_HOST']='1'
 flags['HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT']='1'
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')};env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()})
 (out/'launch-review-environment.json').write_text(json.dumps(flags,indent=2)+'\n')
 write('protocol.json',dict(arm=arm,setupHardBoundSeconds=90,trainReadinessSeconds=20,appearanceArrivalSecondsAfterOpenURLStart=30,observationSecondsAfterRecordedAppearance=30,externalTracePollingSeconds=.03,commandMaxSeconds=20,initialScreenshotUnchanged=True,noAXOrTouches=True,noPhaseOrColorPrerequisite=True,newAppSampler=False,termination='Executor terminates exact launched app PID after helper exit; observation is not extended for cleanup.'))
 tracefolder=data/'Documents'/('HighlightDiagnostic-'+flags['HANGTEN_REVIEW_DIAGNOSTIC_RUN']);assert not tracefolder.exists()
 run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env)
 # New shared startup protocol: observe existing events only; no AX/touch or UI write.
 readinessStart=time.monotonic();readinessStartEpoch=time.time();readinessDeadline=min(setupDeadline,readinessStart+20);ready=None
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
 openURLStart=time.time();appearanceDeadline=time.monotonic()+30
 run('xcrun','simctl','openurl',uid,'hangten://plan/research.max-hangs/workout');openURLEnd=time.time()
 write('workout-openurl-timing.json',dict(startEpoch=openURLStart,endEpoch=openURLEnd,appearanceArrivalDeadlineMonotonic=appearanceDeadline,readinessObservedEpoch=ready['hostObservedEpoch']))
 initialStart=time.time()
 try:
  run('xcrun','simctl','io',uid,'screenshot',out/'launch-initial.png')
 finally:
  shot=out/'launch-initial.png'
  write('launch-initial-capture.json',dict(startEpoch=initialStart,endEpoch=time.time(),exists=shot.exists(),sha256=hashlib.sha256(shot.read_bytes()).hexdigest() if shot.exists() else None,observationAnchorReset=False,command=commands[-1]))
 while remaining()>0:time.sleep(min(.03,max(0,remaining())))
 observe();windowEnd=time.time()
 assert appearance is not None,'No recorded workout appearance within30s arrival bound'
 assert not appearanceObserved['monotonic']>appearanceDeadline,'Appearance arrived after prospective deadline'
 write('observation-end.json',dict(reason='fixed-appearance-plus30',epoch=windowEnd,targetEpoch=appearance['epoch']+30,overshootSeconds=windowEnd-(appearance['epoch']+30),phaseCaptureRequired=False))
except BaseException:
 write('observation-end.json',dict(reason='exception-or-command-censoring',epoch=time.time(),targetEpoch=appearance['epoch']+30 if appearance else None,phaseCaptureRequired=False))
 (out/'failure.txt').write_text(traceback.format_exc());raise
finally:
 if active is not None:stop_owned(active)
 save_trace();write('commands.json',commands)
