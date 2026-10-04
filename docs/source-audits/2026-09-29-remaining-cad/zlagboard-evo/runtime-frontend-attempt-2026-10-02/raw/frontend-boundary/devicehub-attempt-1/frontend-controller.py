#!/usr/bin/env python3
"""Prepared controller; no launch without explicit --launch-reviewed flag."""
from pathlib import Path
import atexit,hashlib,json,os,signal,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[5]
OWNER=Path(os.environ.get('PASEO_WORKTREE_PATH',str(ROOT))).name
assert OWNER=='placid-badger-cad-second-half'
OUT=Path(__file__).resolve().parent
UUID='BDCA0D77-94C2-4A97-900B-443F75C64691'
MARKER=OWNER+'-devicehub-frontend-boundary-2026-10-02'
APP=Path('/Applications/Xcode.app/Contents/Applications/DeviceHub.app')
BIN=APP/'Contents/MacOS/DeviceHub'
child=None;cleaned=False;cleanup_ok=False

def write(name,obj):
 p=OUT/name
 with p.open('x') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def ps():
 r=subprocess.run(['rtk','proxy','ps','-axo','pid=,ppid=,comm=,args='],capture_output=True,text=True,timeout=10)
 r.check_returncode();return r.stdout

def frontends(text):
 # comm is whitespace-free for this known executable path; args may contain spaces.
 found=[]
 for line in text.splitlines():
  parts=line.strip().split(None,3)
  if len(parts)>=3 and (Path(parts[2]).name in {'Simulator','DeviceHub','Devices','DevicesTrampoline'} or '/DeviceHub.app/Contents/MacOS/' in parts[2] or '/Simulator.app/Contents/MacOS/' in parts[2]):
   found.append(dict(pid=int(parts[0]),ppid=int(parts[1]),comm=parts[2],args=parts[3] if len(parts)>3 else ''))
 return found


def verify_device_ownership():
 main=OUT.parent.parent/'ios-diagnosis/ownership.json'
 registered=ROOT/'.context/paseo-owned-simulators'
 pending=ROOT/'.context/paseo-pending-simulators'
 owner=json.loads(main.read_text())
 assert owner['owner']==OWNER and owner['simulator']==UUID,'Main ownership mismatch'
 assert UUID in registered.read_text().splitlines() and UUID in pending.read_text().splitlines(),'Exact UUID not registered in both manifests'
 # This exact prior name is retained in the existing environment-readonly owned-device record.
 expected_name='Hang Ten Paseo placid-badger-cad-second-half Review Pro MigrationDiagnosis20261002 96137'
 assert expected_name.startswith('Hang Ten Paseo '+OWNER+' ')
 result=subprocess.run(['rtk','proxy','xcrun','simctl','list','devices','--json'],capture_output=True,text=True,timeout=15)
 assert result.returncode==0,'Read-only exact-device inventory failed'
 inventory=json.loads(result.stdout)
 matches=[d for devices in inventory['devices'].values() for d in devices if d.get('udid')==UUID]
 assert len(matches)==1 and matches[0]['name']==expected_name and matches[0]['state']=='Booted','Exact owned UUID/name/state mismatch'
 write('existing-device-ownership-verification.json',dict(owner=OWNER,deviceUUID=UUID,deviceName=matches[0]['name'],state=matches[0]['state'],mainOwnershipSHA256=hashlib.sha256(main.read_bytes()).hexdigest(),registeredManifestSHA256=hashlib.sha256(registered.read_bytes()).hexdigest(),pendingManifestSHA256=hashlib.sha256(pending.read_bytes()).hexdigest(),verifiedEpoch=time.time(),scope='Read-only exact owned UUID record only; unrelated inventory is never retained'))

def cleanup():
 global cleaned,cleanup_ok
 if cleaned:return
 cleaned=True
 result=dict(owner=OWNER,marker=MARKER,cleanupEpoch=time.time(),scope='Exact spawned frontend PID only; never simulator device/DD/services',pid=child.pid if child else None)
 try:
  if child is not None:
   # An unreaped direct child retains its PID. poll/wait prevent PID-reuse signalling.
   if child.poll() is None:
    before=ps();write('cleanup-before-frontends.json',frontends(before))
    matches=[r for r in frontends(before) if r['pid']==child.pid]
    assert len(matches)==1 and matches[0]['ppid']==os.getpid() and MARKER in matches[0]['args'] and matches[0]['comm'] in {str(BIN),BIN.name}, 'Exact frontend identity guard failed; leave unknown process untouched'
    child.terminate();result['sentTERM']=True
    try:child.wait(timeout=15)
    except subprocess.TimeoutExpired:
     # Same unreaped child only; no process-group kill or broad name match.
     child.kill();result['sentKILL']=True;child.wait(timeout=10)
   result['childExitStatus']=child.returncode
   after=ps();write('cleanup-after-frontends.json',frontends(after))
   result['exactPIDAbsent']=not any(r['pid']==child.pid for r in frontends(after))
   assert result['exactPIDAbsent']
  else:result['noFrontendCreated']=True
  cleanup_ok=True
 except BaseException:result['failure']=traceback.format_exc()
 result['passed']=cleanup_ok
 write('cleanup.json',result)

def interrupted(sig,frame):raise SystemExit(128+sig)

# EXIT equivalent plus INT/TERM handlers installed before any launch/registration.
atexit.register(cleanup)
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
assert sys.argv[1:]==['--launch-reviewed'], 'Preparation only: explicit reviewed launch flag required'
assert BIN.is_file()
assert not (OUT/'ownership.json').exists()
status=1
try:
 before=ps();write('preflight-frontends.json',frontends(before))
 assert not frontends(before), 'Existing legacy Simulator or DeviceHub frontend found: do not attach, launch, or stop it'
 verify_device_ownership()
 argv=[str(BIN),'-PaseoWorkspaceOwner',MARKER]
 write('pending-ownership.json',dict(owner=OWNER,marker=MARKER,controllerPID=os.getpid(),deviceUUID=UUID,argv=argv,registeredBeforeLaunchEpoch=time.time(),deviceCleanupOwner='Main controller90373; frontend controller must never shut down/delete device or DD'))
 # Prevent INT/TERM between child creation and exact PID registration.
 oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
 try:
  stdout=(OUT/'frontend.stdout').open('xb');stderr=(OUT/'frontend.stderr').open('xb')
  child=subprocess.Popen(argv,stdout=stdout,stderr=stderr,env=dict(os.environ,PASEO_RESOURCE_OWNER=MARKER),start_new_session=True)
  stdout.close();stderr.close()
  write('ownership.json',dict(owner=OWNER,marker=MARKER,controllerPID=os.getpid(),frontendPID=child.pid,deviceUUID=UUID,argv=argv,registeredEpoch=time.time(),resourceType='DeviceHub desktop frontend process',cleanupScope='Only this unreaped direct child PID; no shared services/devices/DD'))
 finally:signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
 time.sleep(1)
 assert child.poll() is None,'Frontend exited during launch; no relaunch'
 after=ps();write('launched-frontends.json',frontends(after));actual=frontends(after)
 assert len(actual)==1 and actual[0]['pid']==child.pid and actual[0]['ppid']==os.getpid() and MARKER in actual[0]['args'] and actual[0]['comm'] in {str(BIN),BIN.name},'Unexpected frontend identity; abort'
 write('frontend-process-ready.json',dict(epoch=time.time(),frontend=actual[0],visibleWindowVerified=False,next='Intended UUID is ownership metadata only, not a CLI selection. Root selects and verifies owned name plus UUID and visible exact-device window through node_repl @oai/sky before any workout launch; process existence alone is insufficient.'))
 print(json.dumps(dict(frontendPID=child.pid,controllerPID=os.getpid(),owner=MARKER,windowGatePending=True)),flush=True)
 deadline=time.monotonic()+1800
 while time.monotonic()<deadline:
  assert child.poll() is None,'Owned frontend exited unexpectedly; no relaunch'
  stop=OUT/'stop-request.txt'
  if stop.exists():
   assert stop.read_text().strip()==MARKER,'Incorrect stop marker'
   status=0;break
  time.sleep(1)
 else:raise RuntimeError('Frontend controller 1800s hard bound reached')
except BaseException:
 write('controller-failure.json',dict(epoch=time.time(),error=traceback.format_exc()));raise
finally:
 cleanup()
 if not cleanup_ok:status=1
sys.exit(status)
