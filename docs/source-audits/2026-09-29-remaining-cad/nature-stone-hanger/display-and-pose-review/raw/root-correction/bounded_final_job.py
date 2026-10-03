from pathlib import Path
import sys,subprocess,os,signal,time,json,datetime,shutil,traceback
w=Path(__file__).resolve().parent;mode=sys.argv[1];name='placid-badger-final-'+mode+'-v2'
receipt=w/(name+'-ownership.json');tmp=w/(name+'-tmp');logpath=w/(name+'.log')
if receipt.exists() or tmp.exists() or logpath.exists():raise RuntimeError('owned output already exists')
p=None;started=time.monotonic();record={'workspaceOwner':'placid-badger','name':name,'mode':mode,'timeoutSeconds':1800,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedTmp':str(tmp),'state':'pending'}
def save():receipt.write_text(json.dumps(record,indent=2)+'\n')
def exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False
save()
try:
 tmp.mkdir();env=dict(os.environ,TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
 with logpath.open('w') as log:
  p=subprocess.Popen([str(Path('.context/placid-badger/venv/bin/python').absolute()),str(w/'run_final_routes.py'),mode],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  record.update(state='running',ownedProcessGroup=p.pid);save()
  p.wait(timeout=1800)
  record['exitCode']=p.returncode
except BaseException as e:
 record.update(failure=repr(e),traceback=traceback.format_exc())
finally:
 if p is not None:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  p.wait(timeout=15)
  for _ in range(30):
   if not exists(p.pid):break
   time.sleep(.1)
  record['ownedProcessGroupAbsent']=not exists(p.pid)
 else:record['ownedProcessGroupAbsent']=True
 if record['ownedProcessGroupAbsent'] and tmp.exists():shutil.rmtree(tmp)
 record.update(ownedTmpAbsent=not tmp.exists(),elapsedSeconds=time.monotonic()-started,state='closed')
 save()
print(json.dumps(record),flush=True)
sys.exit(0 if record.get('exitCode')==0 and record['ownedProcessGroupAbsent'] and record['ownedTmpAbsent'] else 1)
