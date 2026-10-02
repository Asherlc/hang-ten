from pathlib import Path
import subprocess,json,os,time,traceback
scratch=Path('.context/placid-badger-cad-second-half/zlagboard-evo/ios-resume-2026-10-02');out=scratch/'highlight-regression'/'trace-runtime-3';out.mkdir(exist_ok=True)
uid=(scratch/'simulator-ready').read_text().strip();commands=[];results={}
def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);commands.append(cmd);r=subprocess.run(cmd,env=env,capture_output=True,timeout=60)
 (out/f'{n:03d}-stdout.txt').write_bytes(r.stdout);(out/f'{n:03d}-stderr.txt').write_bytes(r.stderr);r.check_returncode();return r.stdout.decode()
def flat(ns):
 rows=[]
 for n in ns:
  if n.get('AXLabel') or n.get('AXUniqueId'):rows.append({k:n.get(k) for k in ['AXLabel','AXUniqueId','AXValue','frame']})
  rows.extend(flat(n.get('children',[])))
 return rows
def capture(name,rows):
 (out/(name+'-ax.json')).write_text(json.dumps(rows,indent=2)+'\n');run('xcrun','simctl','io',uid,'screenshot',out/(name+'.png'))
try:
 env=dict(os.environ,SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='zlagboard.evo',SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID='research.max-hangs',SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE='1',SIMCTL_CHILD_HANGTEN_REVIEW_HIGHLIGHT_TRACE='1')
 run('xcrun','simctl','launch','--terminate-running-process','--stdout='+str((out/'console-stdout.log').resolve()),'--stderr='+str((out/'console-stderr.log').resolve()),uid,'com.hangten.training',env=env)
 run('xcrun','simctl','openurl',uid,'hangten://plan/research.max-hangs/workout')
 deadline=time.monotonic()+70;opened=False;active=False;rest=False
 while time.monotonic()<deadline:
  rows=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)));labels=[r['AXLabel'] or '' for r in rows]
  if not opened and 'Open' in labels:
   capture('open-confirmation',rows);run('/opt/homebrew/bin/axe','tap','--label','Open','--tap-style','physical','--udid',uid);opened=True;continue
  if not active and any('STEP 1 OF' in x for x in labels):
   capture('active-first-hang',rows);time.sleep(2);settled=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)));capture('active-settled',settled);active=True
  if active and not rest and any('STEP 2 OF' in x for x in labels):
   capture('following-rest',rows);time.sleep(8);settled=flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)));capture('following-rest-settled',settled);rest=True;break
  time.sleep(.25)
 results={'planID':'research.max-hangs','activeStateCaptured':active,'followingRestCaptured':rest,'source':'Existing bundled PlanLibrary routine, unchanged. Bilateral 20 mm edge requirement is expected to resolve to edge-20-left and edge-20-right; visual/runtime verification required.','visualHighlightReview':'must inspect raw images; state labels alone do not prove correct highlight'}
 print(json.dumps(results,indent=2))
except Exception:
 (out/'failure.txt').write_text(traceback.format_exc());raise
finally:
 (out/'validation.json').write_text(json.dumps({'results':results,'commands':commands},indent=2)+'\n')
