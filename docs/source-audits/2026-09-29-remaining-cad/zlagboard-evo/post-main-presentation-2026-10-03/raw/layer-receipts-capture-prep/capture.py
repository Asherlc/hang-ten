"""One released post-Main candidate arm; no build, install, source change or device creation."""
from pathlib import Path
import os,sys,json,time,subprocess,signal,atexit,hashlib,re,shlex,traceback
D=Path(__file__).parent;OWNER='placid-badger-cad-second-half';BUNDLE='com.hangten.training'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
releasePath=Path(sys.argv[1]);g=json.loads(releasePath.read_text());assert g['runtimeAuthorized'] and g['exclusiveRuntimeOwnership']
UID=g['simulatorUUID'];controllerPID=g['controllerPID'];ownershipPath=Path(g['ownershipPath'])
assert sha(ownershipPath)==g['ownershipSHA256'];owned=json.loads(ownershipPath.read_text())
assert g['owner']==OWNER and owned['owner']==OWNER and owned['simulatorUUID']==UID and owned['controllerPID']==controllerPID
assert g['boardID'] in ('zlagboard.evo','zlagboard.pro') and g['arm'] in ('control','action','reversal')
assert g['runID']==OWNER+'-post-main-'+g['boardID'].replace('.','-')+'-'+g['arm']
expectedFlags={'HANGTEN_REVIEW_BOARD_ID':g['boardID'],'HANGTEN_REVIEW_PLAN_ID':'research.max-hangs','HANGTEN_REVIEW_LANDSCAPE':'1'}
if g['arm'] in ('control','reversal'):expectedFlags['HANGTEN_REVIEW_SKIP_NONINTERACTIVE_PRESENTATION']='1'
assert g['launchReviewFlags']==expectedFlags, 'Only the arm-specific skip flag is permitted'
assert g['helperSHA256']==sha(__file__) and g['scheduleSHA256']==sha(D/'schedule.json') and g['sourceReferenceSHA256']==sha(g['sourceReferencePath'])
source=json.loads(Path(g['sourceReferencePath']).read_text());schedule=json.loads((D/'schedule.json').read_text())
assert source['approvedByRoot'] is True and g['planID']=='research.max-hangs' and g['appArguments']==['-workoutAudioCuesEnabled','NO']
assert source['commit']==g['sourceCommit'] and source['baselineOnly'] is False
for x in source['files']:assert sha(x['path'])==x['sha256']
assert sha('HangTen/Resources/PlanLibrary.json')==g['planLibrarySHA256']
assert sha(D/'routine-reference.json')==g['routineReferenceSHA256']
reference=json.loads((D/'routine-reference.json').read_text());assert reference['planLibrarySHA256']==g['planLibrarySHA256']
parityPath=Path(g['parityPath']);assert sha(parityPath)==g['paritySHA256'];parity=json.loads(parityPath.read_text());assert parity['allEqual'] and len(parity['checks'])==g['parityCheckCount'] and g['parityCheckCount']>0 and all(x['equal'] for x in parity['checks'])
for x in parity['checks']:assert sha(x['path'])==x['sha256']
out=Path(g['outputDirectory']);assert out.resolve().is_relative_to((Path('.context')/OWNER).resolve());assert out.resolve().is_relative_to((D.parent).resolve());out.mkdir(exist_ok=False)
(out/'routine-reference.json').write_bytes((D/'routine-reference.json').read_bytes());(out/'source-reference.json').write_bytes(Path(g['sourceReferencePath']).read_bytes());(out/'runtime-release.json').write_bytes(releasePath.read_bytes());(out/'schedule.json').write_bytes((D/'schedule.json').read_bytes())
commands=[];captures=[];clock=[];child=None;awake=None;awakeStreams=[];app_pid=None;launch_attempted=False;failure=None;errors=[];start=time.monotonic();deadline=start+300

def write(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
def stop(p):
 if p is not None and p.poll() is None:
  p.terminate()
  try:p.wait(timeout=.5)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=1)
def interrupted(n,f):raise InterruptedError('signal '+str(n))
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
atexit.register(lambda:(stop(child),stop(awake))) # Before either owned child/app is created.
def run(args,env=None,limit=20,cleanup=False,target=None,allow_failure=False):
 global child
 if not cleanup:
  assert time.monotonic()<deadline,'300s bound'
  assert awake is None or awake.poll() is None,'Owned idle-sleep assertion exited'
 row=dict(command=['rtk','proxy',*map(str,args)],startEpoch=time.time(),startMonotonic=time.monotonic(),limitSeconds=limit);commands.append(row)
 if target is not None and row['startMonotonic']-target>.25:
  row['notLaunched']=True;write('commands.json',commands);raise AssertionError('Fixed screenshot deadline missed; no backfill')
 n=len(commands)-1
 with (out/f'{n:03d}-stdout.txt').open('xb') as a,(out/f'{n:03d}-stderr.txt').open('xb') as b:
  child=subprocess.Popen(row['command'],stdout=a,stderr=b,env=env);row['pid']=child.pid;write('commands.json',commands)
  try:
   until=time.monotonic()+limit
   while child.poll() is None:
    if time.monotonic()>until or (not cleanup and time.monotonic()>deadline):raise TimeoutError('Command/300s bound')
    if not cleanup and awake is not None:assert awake.poll() is None,'Owned assertion exited'
    time.sleep(.02)
  except BaseException:row['error']=traceback.format_exc();raise
  finally:stop(child);row.update(endEpoch=time.time(),endMonotonic=time.monotonic(),exitStatus=child.returncode);child=None;write('commands.json',commands)
 if row['exitStatus'] and not allow_failure:raise RuntimeError('Command failed: retained raw output')
 return (out/f'{n:03d}-stdout.txt').read_text().strip()
def wait_until(t):
 while time.monotonic()<t:
  assert time.monotonic()<deadline and awake.poll() is None,'Deadline/assertion failure'
  time.sleep(min(.03,max(0,t-time.monotonic())))
def flat(ns):
 result=[]
 for n in ns:result.append(n);result.extend(flat(n.get('children',[])))
 return result
try:
 lifecycle=Path(owned['lifecyclePath'])
 ps=shlex.split(run(['ps','-p',str(controllerPID),'-o','pid=,command=']));assert ps and ps[0]==str(controllerPID) and any(Path(token).resolve()==lifecycle.resolve() for token in ps[1:])
 assert UID in Path('.context/paseo-owned-simulators').read_text().splitlines()
 assert not (ownershipPath.parent/'cleanup-requested').exists()
 # Exact direct child and lifetime-bound assertion; no shared process/service operation.
 awakeStreams=[(out/'awake.stdout').open('xb'),(out/'awake.stderr').open('xb')]
 awakeCommand=[g['runID']+'-idle-sleep-assertion','-i','-w',str(os.getpid()),'-t','300']
 awake=subprocess.Popen(awakeCommand,executable='/usr/bin/caffeinate',stdout=awakeStreams[0],stderr=awakeStreams[1])
 write('awake-ownership.json',dict(owner=OWNER,resourceName=g['runID']+'-idle-sleep-assertion',pid=awake.pid,parentPID=os.getpid(),command=awakeCommand,executable='/usr/bin/caffeinate',registeredImmediately=True));assert awake.poll() is None
 app=Path(run(['xcrun','simctl','get_app_container',UID,BUNDLE,'app']));assert sha(app/'HangTen.debug.dylib')==g['binarySHA256'];assert all(Path(x['path']).is_relative_to(app) for x in parity['checks'] if x['category']=='installedMachO')
 write('installed-binary-gate.json',dict(path=str(app/'HangTen.debug.dylib'),sha256=sha(app/'HangTen.debug.dylib')))
 flags=dict(expectedFlags)
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')};env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()});write('launch-review-environment.json',flags);write('launch-app-arguments.json',g['appArguments'])
 launch_attempted=True;response=run(['xcrun','simctl','launch','--terminate-running-process','--stdout='+str((out/'app.stdout').resolve()),'--stderr='+str((out/'app.stderr').resolve()),UID,BUNDLE,*g['appArguments']],env=env);match=re.search(r':\s*(\d+)\s*$',response);app_pid=int(match.group(1)) if match else None;write('app-registration.json',dict(owner=OWNER,simulatorUUID=UID,pid=app_pid,bundle=BUNDLE));assert app_pid is not None
 wait_until(time.monotonic()+3)
 # One setup-only AX read; measurements begin only after this and the initial Train screenshot.
 tree=json.loads(run(['/opt/homebrew/bin/axe','describe-ui','--udid',UID]));nodes=flat(tree);assert any(n.get('AXUniqueId')=='train.settings' for n in nodes) and any(n.get('AXUniqueId')=='train.board' and n.get('AXLabel')==('Zlagboard.Evo' if g['boardID']=='zlagboard.evo' else 'Zlagboard.Pro 2.0') for n in nodes),'Normal Train and expected board setup not present; stop without retry'
 write('train-setup-ax.json',tree);run(['xcrun','simctl','io',UID,'screenshot',out/'train-setup.png'])
 routeStart=dict(epoch=time.time(),monotonic=time.monotonic());run(['xcrun','simctl','openurl',UID,'hangten://plan/research.max-hangs/workout']);anchor=dict(epoch=time.time(),monotonic=time.monotonic());write('external-anchor.json',dict(routeStart=routeStart,routeCompleted=anchor,noAppPhaseInference=True))
 # After openurl, screenshots only: no AX, taps, gesture, pause, skip or relaunch.
 for offset in schedule['offsetSeconds']:
  target=anchor['monotonic']+offset;wait_until(target);name=f'elapsed-{offset:03d}s.png';run(['xcrun','simctl','io',UID,'screenshot',out/name],target=target);c=commands[-1]
  captures.append(dict(path=str(out/name),sha256=sha(out/name),scheduledOffset=offset,targetMonotonic=target,startEpoch=c['startEpoch'],endEpoch=c['endEpoch'],startMonotonic=c['startMonotonic'],endMonotonic=c['endMonotonic'],latenessSeconds=c['startMonotonic']-target,phase='UNCLASSIFIED_REQUIRES_WHOLE_IMAGE_REVIEW'));write('captures.json',captures)
 assert len(captures)==len(schedule['offsetSeconds'])
except BaseException:failure=traceback.format_exc();(out/'failure.txt').write_text(failure)
finally:
 stop(child)
 cleanup=dict(scope='Exact app and own awake direct child only; persistent Simulator/DD remain controller-owned')
 if launch_attempted:
  try:
   run(['xcrun','simctl','terminate',UID,BUNDLE],cleanup=True,limit=10,allow_failure=True)
   q=run(['ps','-p',str(app_pid),'-o','pid=,comm='],cleanup=True,limit=3,allow_failure=True) if app_pid else None
   cleanup['appPIDAbsent']=bool(app_pid) and commands[-1]['exitStatus']==1 and not q
  except BaseException:cleanup['error']=traceback.format_exc()
 stop(awake);cleanup['awakeChildReaped']=awake is None or awake.poll() is not None;cleanup['awakeExitStatus']=awake.returncode if awake else None
 if awake is not None:
  try:
   q=run(['ps','-p',str(awake.pid),'-o','pid=,comm='],cleanup=True,limit=3,allow_failure=True);cleanup['awakePIDAbsent']=commands[-1]['exitStatus']==1 and not q
  except BaseException:cleanup['awakePIDAbsent']=False;cleanup['awakeVerificationError']=traceback.format_exc()
 else:cleanup['awakePIDAbsent']=True
 for f in awakeStreams:f.close()
 cleanup['passed']=(not launch_attempted or cleanup.get('appPIDAbsent') is True) and cleanup['awakeChildReaped'] and cleanup['awakePIDAbsent'] and 'error' not in cleanup;write('cleanup.json',cleanup)
 if not cleanup['passed']:errors.append('Exact cleanup not verified')
 for x in source['files']+parity['checks']:
  try:
   if sha(x['path'])!=x['sha256']:errors.append('Post-run parity changed: '+x['path'])
  except Exception:errors.append('Post-run parity unavailable: '+x['path'])
 offsets=[c[k+'Epoch']-c[k+'Monotonic'] for c in commands for k in ('start','end') if k+'Epoch' in c];spread=max(offsets)-min(offsets) if offsets else None;stable=spread is not None and spread<=.1;write('host-clock-stability.json',dict(offsets=offsets,spreadSeconds=spread,thresholdSeconds=.1,passed=stable,noAppClockAvailable=True))
 if not stable:errors.append('Host clock drift; no timing comparison')
 write('captures.json',captures);write('commands.json',commands);write('completion.json',dict(captureCompleted=failure is None and not errors,plannedCaptures=len(schedule['offsetSeconds']),actualCaptures=len(captures),errors=errors,visualResult='PENDING_WHOLE_IMAGE_REVIEW',CPUBracketsAvailable=False,phaseTimingsKnown=False,noRetries=True))
if failure or errors:raise SystemExit(1)
