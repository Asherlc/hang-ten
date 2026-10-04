from pathlib import Path
import subprocess,json,os,time,traceback
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');out=base/'visibility-a-landscape';out.mkdir(exist_ok=False)
uid='BDCA0D77-94C2-4A97-900B-443F75C64691';commands=[];events=[]
def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];start=time.time();n=len(commands)
 try:r=subprocess.run(cmd,env=env,capture_output=True,timeout=25)
 except subprocess.TimeoutExpired as e:
  (out/f'{n:03d}-timeout-stdout.txt').write_bytes(e.stdout or b'');(out/f'{n:03d}-timeout-stderr.txt').write_bytes(e.stderr or b'');commands.append({'command':cmd,'startEpoch':start,'endEpoch':time.time(),'timedOut':True});raise
 (out/f'{n:03d}-stdout.txt').write_bytes(r.stdout);(out/f'{n:03d}-stderr.txt').write_bytes(r.stderr);commands.append({'command':cmd,'startEpoch':start,'endEpoch':time.time(),'exitStatus':r.returncode});r.check_returncode();return r.stdout
try:
 env=dict(os.environ,SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='zlagboard.evo',SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID='research.max-hangs',SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE='1',SIMCTL_CHILD_HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC='1',SIMCTL_CHILD_HANGTEN_REVIEW_DIAGNOSTIC_RUN='placid-badger-cad-second-half-visibility-a',SIMCTL_CHILD_HANGTEN_REVIEW_ENTITY_VISIBILITY_PROBE='1')
 for k in ['SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ARVIEW_HOST','SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_VIRTUAL_CAMERA','SIMCTL_CHILD_HANGTEN_REVIEW_SUPPRESS_WORKOUT_HAND_HOST']:env.pop(k,None)
 (out/'launch-review-environment.json').write_text(json.dumps({k:v for k,v in env.items() if k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')},indent=2)+'\n')
 run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env)
 run('xcrun','simctl','openurl',uid,'hangten://plan/research.max-hangs/workout')
 for i in range(40):
  name=f'window-{i:02d}';start=time.time();run('xcrun','simctl','io',uid,'screenshot',out/(name+'.png'));events.append({'capture':name,'startEpoch':start,'endEpoch':time.time()});time.sleep(.25)
except Exception:
 (out/'failure.txt').write_text(traceback.format_exc());raise
finally:
 (out/'validation.json').write_text(json.dumps({'events':events,'commands':commands,'scope':'Dense actual workout captures; no pause/skip/seek/camera actions; DEBUG selected-entity visibility only'},indent=2)+'\n')
