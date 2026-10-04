from pathlib import Path
import subprocess,json,time,os,traceback
s=Path('.context/placid-badger-cad-second-half/zlagboard-pro/ios-26-5-2026-10-02');out=s/'elevated-jugs-gentle';out.mkdir(exist_ok=False);uid=(s/'simulator-ready').read_text().strip();commands=[];checks=[]
def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);commands.append(cmd);r=subprocess.run(cmd,env=env,capture_output=True,timeout=30);(out/f'{n:03d}-stdout.txt').write_bytes(r.stdout);(out/f'{n:03d}-stderr.txt').write_bytes(r.stderr);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');r.check_returncode();return r.stdout.decode()
def flat(ns):
 rows=[]
 for n in ns:
  if n.get('AXLabel') or n.get('AXUniqueId'):rows.append({k:n.get(k) for k in ['AXLabel','AXUniqueId','frame']})
  rows.extend(flat(n.get('children',[])))
 return rows
try:
 for side,dx in [('left',25),('right',-25)]:
  contact='top-jug-'+side;env=dict(os.environ,SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='zlagboard.pro',SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_DETAIL='1',SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_HOLD_ID=contact)
  run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env);time.sleep(3)
  for attempt in range(45):
   before=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)))
   if len([r for r in before if (r['AXUniqueId'] or '').startswith('boardModel.contact.')])==28:break
   time.sleep(1)
  else:raise RuntimeError('No loaded 28-contact board')
  f=next(x['frame'] for x in before if x['AXUniqueId']=='boardDetail.map');x=f['x']+f['width']/2;y=f['y']+f['height']*.65
  run('/opt/homebrew/bin/axe','swipe','--start-x',x,'--start-y',y,'--end-x',x+dx,'--end-y',y-48,'--duration','1.0','--udid',uid);time.sleep(2)
  rows=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)));assert any(r['AXUniqueId']=='boardDetail.selectedHold.'+contact for r in rows)
  (out/(side+'-elevated-accessibility.json')).write_text(json.dumps(rows,indent=2)+'\n');run('xcrun','simctl','io',uid,'screenshot',out/(side+'-elevated.png'));checks.append({'contactID':contact,'image':side+'-elevated.png','gestureDelta':[dx,-48],'selectedConfirmed':True})
except Exception:(out/'failure.txt').write_text(traceback.format_exc());raise
finally:(out/'validation.json').write_text(json.dumps({'checks':checks,'purpose':'Actual UI orbit to expose entire jug crest and outer corners; no package/camera modification, no source image measurement.','visualReview':'pending Astra inspection'},indent=2)+'\n')
