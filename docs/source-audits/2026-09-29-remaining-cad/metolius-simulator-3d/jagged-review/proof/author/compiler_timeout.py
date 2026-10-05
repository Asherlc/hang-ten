import subprocess,time,json,os,signal
from pathlib import Path
w=Path(__file__).resolve().parent
jobs={67048:'check',81961:'export'};ended={}
while jobs:
 for pid,name in list(jobs.items()):
  r=subprocess.run(['ps','-p',str(pid),'-o','etime=,command='],text=True,capture_output=True)
  if r.returncode or not r.stdout.strip():ended[name]='exited';del jobs[pid];continue
  line=r.stdout.strip()
  if '/metolius-simulator-3d-jagged/native-author/' not in line or 'freecadcmd' not in line:ended[name]='ownership no longer matches';del jobs[pid];continue
  parts=line.split()[0].replace('-',':').split(':');elapsed=sum(int(x)*m for x,m in zip(reversed(parts),[1,60,3600,86400]))
  if elapsed>=1800:os.kill(pid,signal.SIGTERM);ended[name]='terminated at 30 minute bound';del jobs[pid]
 (w/'compiler-timeout-status.json').write_text(json.dumps({'active':jobs,'ended':ended,'limitSeconds':1800},indent=2)+'\n')
 if jobs:time.sleep(5)
