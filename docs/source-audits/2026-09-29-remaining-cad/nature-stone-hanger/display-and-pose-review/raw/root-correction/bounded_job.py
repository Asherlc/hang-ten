import sys,subprocess,os,signal,time,json,datetime
from pathlib import Path
w=Path(__file__).resolve().parent;name=sys.argv[1];script=sys.argv[2];timeout=int(sys.argv[3]) if len(sys.argv)>3 else 600
out=w/(name+'.log');tmp=w/(name+'-tmp');tmp.mkdir(exist_ok=True);env=dict(os.environ,TMPDIR=str(tmp));start=time.monotonic();p=None
record={'workspaceOwner':'placid-badger','name':name,'script':script,'timeoutSeconds':timeout,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
try:
 with out.open('w') as log:
  p=subprocess.Popen([str(Path('.context/placid-badger/venv/bin/python').absolute()),script],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);record['ownedProcessGroup']=p.pid;(w/(name+'-ownership.json')).write_text(json.dumps(record,indent=2))
  try:p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
finally:
 if p is not None and p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
 record.update(elapsedSeconds=time.monotonic()-start,exitCode=p.returncode if p else None,ownedProcessGroupExited=p is None or p.poll() is not None);(w/(name+'-ownership.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record));sys.exit(p.returncode if p else 1)
