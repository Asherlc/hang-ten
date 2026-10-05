import sys, os, json, hashlib, signal, atexit, shutil, subprocess, time
from pathlib import Path
root=Path.cwd();out=Path(__file__).resolve().parent
stage=sys.argv[1]
assert stage in ("check","publish","reproduction","pocket-surfaces")
owner="placid-badger-cad-second-half"
work=out/("temporary-"+owner+"-"+stage)
registry=out/(stage+"-resources.json")
child=None
record={"owner":owner,"stage":stage,"exactTemporaryDirectory":str(work),"childPID":None,"created":False}
def write_record():registry.write_text(json.dumps(record,indent=2)+"\n")
def cleanup():
 global child
 if child is not None and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:child.kill();child.wait()
 if record["created"] and work.exists():shutil.rmtree(work)
 record["verifiedTemporaryDirectoryDeleted"]=not work.exists()
 record["childExited"]=child is None or child.poll() is not None
 write_record()
def interrupted(signum,frame):
 cleanup();raise SystemExit(128+signum)
atexit.register(cleanup)
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
assert not work.exists(),work
write_record();work.mkdir();record["created"]=True;write_record()
source=root/"Hangboards/zlagboard-pro/zlagboard-pro.FCStd"
source_before=hashlib.sha256(source.read_bytes()).hexdigest()
report=out/(stage+".json");status=out/(stage+"-inner-status.json")
assert not report.exists() and not status.exists(), "Never overwrite retained proofs"
if stage in ("check","publish"):
 args=["--package","zlagboard-pro","--report",str(report)]
 if stage=="check":args += ["--check","--assets",str(work/"assets")]
 script="import sys,os,json,traceback\nfrom pathlib import Path\n"
 script+=f"sys.path.insert(0,{str(root/'Tools/HangboardCAD')!r})\n"
 script+="import FreeCAD,Part\nprint('Pinned FreeCAD',FreeCAD.Version(),'OCCT',Part.OCC_VERSION,flush=True)\n"
 script+="code=0\ntry:\n import compile_board\n code=compile_board.main("+repr(args)+")\nexcept BaseException:\n traceback.print_exc()\n code=3\nfinally:\n Path("+repr(str(status))+").write_text(json.dumps({'exitCode':code})+'\\n')\n sys.stdout.flush();sys.stderr.flush()\n"
 wrapper=out/(stage+"-freecad.py");wrapper.write_text(script)
 command=["/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",str(wrapper)]
elif stage=="pocket-surfaces":
 command=["/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",str(out/"compare_pocket_surfaces.py")]
else:
 command=[sys.executable,str(out/"run_reproduction.py"),str(work),str(report)]
environment=dict(os.environ,TMPDIR=str(work),HANGTEN_CAD_PYTHONPATH="/Users/asherlc/.paseo/worktrees/0h78jp9r/placid-badger/.context/placid-badger/pxr311")
record["command"]=command;record["sourceSHA256Before"]=source_before;write_record();started=time.monotonic()
with (out/(stage+".stdout.log")).open("xb") as stdout,(out/(stage+".stderr.log")).open("xb") as stderr:
 child=subprocess.Popen(command,env=environment,stdout=stdout,stderr=stderr)
 record["childPID"]=child.pid;write_record();code=child.wait()
source_after=hashlib.sha256(source.read_bytes()).hexdigest()
result={"stage":stage,"childExitCode":code,"reportExists":report.exists(),"sourceSHA256Before":source_before,"sourceSHA256After":source_after,"sourceUnchanged":source_before==source_after,"elapsedSeconds":time.monotonic()-started}
if stage in ("check","publish"):
 # FreeCAD's launcher can swallow Python exceptions: require our exact report too.
 result["innerStatusExists"]=status.exists()
 if status.exists():result["innerExitCode"]=json.loads(status.read_text())["exitCode"]
result["passed"]=code==0 and report.exists() and source_before==source_after and result.get("innerExitCode",0)==0
(out/(stage+"-status.json")).write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2),flush=True)
cleanup()
raise SystemExit(0 if result["passed"] else 1)
