import sys,subprocess,os,signal,time,json,hashlib,datetime
from pathlib import Path
w=Path(__file__).resolve().parent;name=sys.argv[1];args=sys.argv[2:];log=w/(name+'.log');report=w/(name+'.json');tmp=w/(name+'-tmp');tmp.mkdir(exist_ok=True);env=dict(os.environ);env['TMPDIR']=str(tmp);start=time.monotonic();proc=None
record={'workspaceOwner':'placid-badger','name':name,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeoutSeconds':900,'compilerSHA256':hashlib.sha256(Path('Tools/HangboardCAD/compile_board.py').read_bytes()).hexdigest(),'args':args}
try:
 with log.open('w') as out:
  cmd=[sys.executable,'Tools/HangboardCAD/run_freecad.py','--extra-python-path','.context/placid-badger/pxr311','Tools/HangboardCAD/compile_board.py']+args+['--report',str(report)]
  proc=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT,env=env,start_new_session=True);record['ownedProcessGroup']=proc.pid;(w/(name+'-ownership.json')).write_text(json.dumps(record,indent=2)+'\n')
  try:code=proc.wait(timeout=900)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   code=124
finally:
 if proc is not None and proc.poll() is None:
  os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
 record['compilerSHA256After']=hashlib.sha256(Path('Tools/HangboardCAD/compile_board.py').read_bytes()).hexdigest();record['compilerBytesUnchanged']=record['compilerSHA256After']==record['compilerSHA256'];record['elapsedSeconds']=time.monotonic()-start;record['exitCode']=proc.returncode if proc else None;record['ownedProcessGroupExited']=proc is None or proc.poll() is not None;(w/(name+'-ownership.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2));raise SystemExit(code)
