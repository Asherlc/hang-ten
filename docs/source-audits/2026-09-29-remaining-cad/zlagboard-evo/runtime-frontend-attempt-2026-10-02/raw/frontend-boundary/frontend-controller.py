#!/usr/bin/env python3
"""Prepared controller; no launch without explicit --launch-reviewed flag."""
from pathlib import Path
import atexit,hashlib,json,os,signal,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[4]
OWNER=Path(os.environ.get('PASEO_WORKTREE_PATH',str(ROOT))).name
assert OWNER=='placid-badger-cad-second-half'
OUT=Path(__file__).resolve().parent
UUID='BDCA0D77-94C2-4A97-900B-443F75C64691'
MARKER=OWNER+'-frontend-boundary-2026-10-02'
APP=Path('/Applications/Xcode.app/Contents/Developer/Applications/Simulator.app')
BIN=APP/'Contents/MacOS/Simulator'
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
  if len(parts)>=3 and (parts[2].endswith('/Simulator.app/Contents/MacOS/Simulator') or parts[2]=='Simulator'):
   found.append(dict(pid=int(parts[0]),ppid=int(parts[1]),comm=parts[2],args=parts[3] if len(parts)>3 else ''))
 return found

def cleanup():
 global cleaned,cleanup_ok
 if cleaned:return
 cleaned=True
 result=dict(owner=OWNER,marker=MARKER,cleanupEpoch=time.time(),scope='Exact spawned frontend PID only; never simulator device/DD/services',pid=child.pid if child else None)
 try:
  if child is not None:
   # An unreaped direct child retains its PID. poll/wait prevent PID-reuse signalling.
   if child.poll() is None:
    before=ps();(OUT/'cleanup-before-ps.txt').write_text(before)
    matches=[r for r in frontends(before) if r['pid']==child.pid]
    assert len(matches)==1 and matches[0]['ppid']==os.getpid() and MARKER in matches[0]['args'] and UUID in matches[0]['args'], 'Exact frontend identity guard failed; leave unknown process untouched'
    child.terminate();result['sentTERM']=True
    try:child.wait(timeout=15)
    except subprocess.TimeoutExpired:
     # Same unreaped child only; no process-group kill or broad name match.
     child.kill();result['sentKILL']=True;child.wait(timeout=10)
   result['childExitStatus']=child.returncode
   after=ps();(OUT/'cleanup-after-ps.txt').write_text(after)
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
 before=ps();(OUT/'preflight-ps.txt').write_text(before)
 assert not frontends(before), 'Existing Simulator frontend found: do not attach, launch, or stop it'
 argv=[str(BIN),'-CurrentDeviceUDID',UUID,'-PaseoWorkspaceOwner',MARKER]
 write('pending-ownership.json',dict(owner=OWNER,marker=MARKER,controllerPID=os.getpid(),deviceUUID=UUID,argv=argv,registeredBeforeLaunchEpoch=time.time(),deviceCleanupOwner='Main controller90373; frontend controller must never shut down/delete device or DD'))
 # Prevent INT/TERM between child creation and exact PID registration.
 oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
 try:
  stdout=(OUT/'frontend.stdout').open('xb');stderr=(OUT/'frontend.stderr').open('xb')
  child=subprocess.Popen(argv,stdout=stdout,stderr=stderr,env=dict(os.environ,PASEO_RESOURCE_OWNER=MARKER),start_new_session=True)
  stdout.close();stderr.close()
  write('ownership.json',dict(owner=OWNER,marker=MARKER,controllerPID=os.getpid(),frontendPID=child.pid,deviceUUID=UUID,argv=argv,registeredEpoch=time.time(),resourceType='Simulator desktop frontend process',cleanupScope='Only this unreaped direct child PID; no shared services/devices/DD'))
 finally:signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
 time.sleep(1)
 assert child.poll() is None,'Frontend exited during launch; no relaunch'
 after=ps();(OUT/'launched-ps.txt').write_text(after);actual=frontends(after)
 assert len(actual)==1 and actual[0]['pid']==child.pid and actual[0]['ppid']==os.getpid() and MARKER in actual[0]['args'] and UUID in actual[0]['args'],'Unexpected frontend identity; abort'
 write('frontend-process-ready.json',dict(epoch=time.time(),frontend=actual[0],visibleWindowVerified=False,next='Root verifies visible exact-device window through node_repl @oai/sky before any workout launch; process existence alone is insufficient.'))
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
