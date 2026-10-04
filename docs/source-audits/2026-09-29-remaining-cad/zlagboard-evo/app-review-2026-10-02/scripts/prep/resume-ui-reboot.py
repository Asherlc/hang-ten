from pathlib import Path
import subprocess,json,os,signal,time
out=Path('.context/placid-badger-cad-second-half/zlagboard-evo/ios-resume-2026-10-02/ui-reboot');out.mkdir(exist_ok=False);uid='1684856E-FC2D-4407-8063-9B343B99CAD6';records=[]
def run(name,args,timeout):
 cmd=['rtk','proxy',*args];start=time.monotonic();record={'name':name,'command':cmd,'timeoutSeconds':timeout}
 with (out/(name+'.log')).open('wb') as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:status=proc.wait(timeout=timeout)
  except subprocess.TimeoutExpired:record['timedOut']=True;os.killpg(proc.pid,signal.SIGTERM);status=proc.wait(timeout=15)
 record.update(exitStatus=status,elapsedSeconds=time.monotonic()-start);records.append(record);(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');return status
assert run('shutdown',['xcrun','simctl','shutdown',uid],45)==0
assert run('boot',['xcrun','simctl','boot',uid],45)==0
status=run('bootstatus',['xcrun','simctl','bootstatus',uid,'-b'],480)
run('frontend',['open','-a','Simulator','--args','-CurrentDeviceUDID',uid],15)
run('screen',['xcrun','simctl','io',uid,'screenshot',str(out/'view.png')],20)
run('accessibility',['/opt/homebrew/bin/axe','describe-ui','--udid',uid],20)
print('Same owned UUID shutdown/boot completed; bootstatus',status)
