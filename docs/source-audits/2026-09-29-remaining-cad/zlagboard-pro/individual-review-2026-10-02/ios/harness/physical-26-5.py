from pathlib import Path
import json,os,subprocess,time,sys,traceback
root=Path.cwd();s=root/'.context/placid-badger-cad-second-half/zlagboard-pro/ios-26-5-2026-10-02'; out=s/'physical-probes';out.mkdir(exist_ok=True)
uid=(s/'simulator-ready').read_text().strip();label=sys.argv[1];action=sys.argv[2];dest=out/label;dest.mkdir(exist_ok=False);commands=[]
def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);commands.append(cmd);r=subprocess.run(cmd,env=env,capture_output=True,timeout=60)
 (dest/f'{n:03d}-stdout.txt').write_bytes(r.stdout);(dest/f'{n:03d}-stderr.txt').write_bytes(r.stderr);r.check_returncode();return r.stdout.decode()
def flat(ns):
 rows=[]
 for n in ns:
  if n.get('AXLabel') or n.get('AXUniqueId'):rows.append({k:n.get(k) for k in ['AXLabel','AXUniqueId','AXValue','frame']})
  rows.extend(flat(n.get('children',[])))
 return rows
try:
 if action=='launch':
  env=dict(os.environ,SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='zlagboard.pro',SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_DETAIL='1',SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_HOLD_ID=sys.argv[3])
  run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env);time.sleep(3)
 elif action=='orbit':
  rows=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)));f=next(r['frame'] for r in rows if r['AXUniqueId']=='boardDetail.map')
  run('/opt/homebrew/bin/axe','swipe','--start-x',f['x']+f['width']*.4,'--start-y',f['y']+f['height']*.5,'--end-x',f['x']+f['width']*.58,'--end-y',f['y']+f['height']*.5,'--duration','1.0','--udid',uid);time.sleep(1)
 elif action=='tap-contact':
  rows=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)));f=next(r['frame'] for r in rows if r['AXUniqueId']=='boardModel.contact.'+sys.argv[3])
  run('/opt/homebrew/bin/axe','tap','-x',f['x']+f['width']/2,'-y',f['y']+f['height']/2,'--tap-style','physical','--udid',uid);time.sleep(2)
 elif action=='tap':
  run('/opt/homebrew/bin/axe','tap','-x',sys.argv[3],'-y',sys.argv[4],'--tap-style','physical','--udid',uid);time.sleep(2)
 else:raise ValueError(action)

 for attempt in range(45):
  rows=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)))
  if len([r for r in rows if (r['AXUniqueId'] or '').startswith('boardModel.contact.')])==28 and not any(r['AXUniqueId']=='boardModel.loading' for r in rows):break
  time.sleep(1)
 else:raise RuntimeError('Board never became ready with all 28 contacts')
 (dest/'accessibility.json').write_text(json.dumps(rows,indent=2)+'\n');run('xcrun','simctl','io',uid,'screenshot',dest/'view.png')
 print(json.dumps({'label':label,'selected':[r['AXUniqueId'] for r in rows if (r['AXUniqueId'] or '').startswith('boardDetail.selectedHold.')]},indent=2))
except Exception:
 (dest/'failure.txt').write_text(traceback.format_exc());raise
finally:(dest/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
