from pathlib import Path
import subprocess,json,sys,signal,os,time
uid,out=sys.argv[1:];out=Path(out);records=[];proc=None
def stop(signum,frame):
 if proc is not None and proc.poll() is None:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=15)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
 raise SystemExit(128+signum)
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def run(name,args,timeout):
 global proc
 cmd=['rtk','proxy',*args];record={'name':name,'command':cmd,'timeoutSeconds':timeout};start=time.monotonic()
 with (out/(name+'.log')).open('wb') as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:status=proc.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   record['timedOut']=True;os.killpg(proc.pid,signal.SIGTERM)
   try:status=proc.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);status=proc.wait(timeout=5)
 record.update(exitStatus=status,elapsedSeconds=time.monotonic()-start);records.append(record);(out/'boot-recovery-commands.json').write_text(json.dumps(records,indent=2)+'\n');return status
first=run('boot-first',['xcrun','simctl','bootstatus',uid,'-b'],180)
if first!=0:
 run('first-timeout-screen',['xcrun','simctl','io',uid,'screenshot',str(out/'first-timeout-screen.png')],20)
 shutdown=run('owned-reboot-shutdown',['xcrun','simctl','shutdown',uid],45);assert shutdown==0,shutdown
 boot=run('owned-reboot-boot',['xcrun','simctl','boot',uid],45);assert boot==0,boot
 second=run('boot-after-reboot',['xcrun','simctl','bootstatus',uid,'-b'],480)
 if second!=0:run('final-timeout-screen',['xcrun','simctl','io',uid,'screenshot',str(out/'final-timeout-screen.png')],20)
 assert second==0,second
(out/'boot-ready.json').write_text(json.dumps({'simulatorUUID':uid,'ready':True,'ordinaryRebootUsed':first!=0,'records':'boot-recovery-commands.json'},indent=2)+'\n')
