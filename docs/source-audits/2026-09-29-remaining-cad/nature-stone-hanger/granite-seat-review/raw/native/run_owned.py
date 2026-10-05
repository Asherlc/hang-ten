from pathlib import Path
import subprocess,os,sys,json,signal,time,shutil,atexit
w=Path(__file__).resolve().parent
name='placid-badger-'+Path(sys.argv[1]).stem
tmp=w/(name+'-tmp');tmp.mkdir(exist_ok=True)
record={'owner':'placid-badger','name':name,'tempPath':str(tmp),'timeoutSeconds':240}
rp=w/(name+'-ownership.json');rp.write_text(json.dumps(record,indent=2))
p=None
def cleanup():
 if p is not None:
  try: os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError: pass
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL);p.wait()
 shutil.rmtree(tmp)
 record['tempDeleted']=not tmp.exists()
 try:os.killpg(p.pid,0);record['processGroupExited']=False
 except ProcessLookupError:record['processGroupExited']=True
 rp.write_text(json.dumps(record,indent=2))
atexit.register(cleanup)
env=dict(os.environ,TMPDIR=str(tmp.resolve()))
with (w/(name+'.log')).open('w') as log:
 p=subprocess.Popen([sys.executable,'Tools/HangboardCAD/run_freecad.py',str(w/sys.argv[1])],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
 record['processGroup']=p.pid;rp.write_text(json.dumps(record,indent=2))
 try:record['exitCode']=p.wait(timeout=240)
 except subprocess.TimeoutExpired:record['timeout']=True;raise
print((w/(name+'.log')).read_text())
raise SystemExit(record['exitCode'])
