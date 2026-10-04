from pathlib import Path
import os, sys, json, time, subprocess, signal, atexit, hashlib, traceback
OWNER="placid-badger-cad-second-half"
P=Path(__file__).resolve().parent
release=Path(sys.argv[1]).resolve(); d=json.loads(release.read_text())
assert d["owner"]==OWNER and d["idleSleepAssertionRequired"] is True and d["maximumClockOffsetRangeSeconds"]==.1
run=P/(d["arm"]+"-awake-ownership");run.mkdir(exist_ok=False)
awake=None;child=None;childCode=None;error=None;cleaned=False
write=lambda n,v:(run/n).write_text(json.dumps(v,indent=2)+"\n")
def interrupted(n,f):raise InterruptedError("signal "+str(n))
def cleanup():
 global cleaned
 if cleaned:return
 result={"owner":OWNER}
 if child is not None:
  if child.poll() is None:
   child.terminate()
   try:child.wait(timeout=25)
   except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
  result["captureChildReaped"]=child.poll() is not None
 if awake is not None:
  if awake.poll() is None:awake.terminate()
  try:awake.wait(timeout=3)
  except subprocess.TimeoutExpired:awake.kill();awake.wait(timeout=3)
  result["assertionPID"]=awake.pid;result["assertionChildReaped"]=awake.poll() is not None
  q=subprocess.run(["rtk","proxy","ps","-p",str(awake.pid),"-o","pid="],capture_output=True,timeout=3)
  (run/"assertion-absence.stdout").write_bytes(q.stdout);(run/"assertion-absence.stderr").write_bytes(q.stderr)
  result["assertionPIDAbsent"]=q.returncode==1 and not q.stdout.strip()
 result["passed"]=result.get("captureChildReaped",True) and result.get("assertionChildReaped",True) and result.get("assertionPIDAbsent",True)
 write("cleanup.json",result);cleaned=True
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted);atexit.register(cleanup)
# Handlers/exit cleanup are installed BEFORE external resource creation.
try:
 with (run/"caffeinate.stdout").open("xb") as o,(run/"caffeinate.stderr").open("xb") as e:
  args=[OWNER+"-idle-sleep-assertion","-i","-w",str(os.getpid()),"-t","360"]
  awake=subprocess.Popen(args,executable="/usr/bin/caffeinate",stdout=o,stderr=e)
  write("ownership.json",{"owner":OWNER,"resourceType":"idle-system-sleep-assertion-process","pid":awake.pid,"parentPID":os.getpid(),"executable":"/usr/bin/caffeinate","argv":args,"createdEpoch":time.time(),"createdMonotonic":time.monotonic(),"cleanupRegisteredBeforeCreation":True})
  assert awake.poll() is None,"Sleep assertion did not remain running"
  with (run/"capture.stdout").open("xb") as a,(run/"capture.stderr").open("xb") as b:
   cmd=[sys.executable,str(P/"capture.py"),str(release)]
   child=subprocess.Popen(cmd,stdout=a,stderr=b)
   write("capture-child.json",{"owner":OWNER,"pid":child.pid,"parentPID":os.getpid(),"command":cmd,"startEpoch":time.time(),"startMonotonic":time.monotonic()})
   limit=time.monotonic()+340
   while child.poll() is None:
    assert awake.poll() is None,"Sleep assertion exited during capture"
    if time.monotonic()>limit:raise TimeoutError("Capture wrapper340s bound")
    time.sleep(.1)
   childCode=child.returncode
except BaseException:error=traceback.format_exc();(run/"failure.txt").write_text(error)
finally:
 cleanup();write("completion.json",{"captureExitStatus":childCode,"wrapperError":error,"cleanupPassed":json.loads((run/"cleanup.json").read_text())["passed"]})
if error or childCode!=0 or not json.loads((run/"cleanup.json").read_text())["passed"]:raise SystemExit(1)
