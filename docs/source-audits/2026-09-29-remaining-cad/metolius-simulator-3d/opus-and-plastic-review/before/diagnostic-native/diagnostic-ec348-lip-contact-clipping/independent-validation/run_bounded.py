import sys,subprocess,os,signal,time,json,shutil
from pathlib import Path
p=Path(__file__).resolve().parent;name=sys.argv[1];timeout=int(sys.argv[2]);args=sys.argv[3:];tmp=p/(name+'-tmp');tmp.mkdir();start=time.monotonic();proc=None;record={'owner':'placid-badger','name':name,'timeoutSeconds':timeout,'command':args}
try:
 with (p/(name+'.log')).open('w') as log:
  proc=subprocess.Popen([sys.executable,'Tools/HangboardCAD/run_freecad.py',*args],stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,TMPDIR=str(tmp.resolve()),XDG_CACHE_HOME=str(tmp.resolve())),start_new_session=True);record['ownedProcessGroup']=proc.pid;(p/(name+'-ownership.json')).write_text(json.dumps(record,indent=2))
  proc.wait(timeout=timeout)
finally:
 if proc is not None:
  try:os.killpg(proc.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  proc.wait()
 shutil.rmtree(tmp);record.update(exitCode=proc.returncode if proc else None,elapsedSeconds=time.monotonic()-start,ownedGroupCleaned=True,tempRemoved=not tmp.exists());(p/(name+'-ownership.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record));raise SystemExit(proc.returncode if proc else 1)
