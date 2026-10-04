from pathlib import Path
import subprocess,json,os,time,traceback,sys,datetime
base=Path('.context/placid-badger-cad-second-half/zlagboard-pro/ios-26-5-2026-10-02');mode=sys.argv[1];assert mode in ['portrait','landscape'];out=base/(sys.argv[2]+'-'+mode);out.mkdir(parents=True,exist_ok=False)
uid=(base/'simulator-ready').read_text().strip();commands=[];results={};events=[]
def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);start=time.time();r=subprocess.run(cmd,env=env,capture_output=True,timeout=60);commands.append({'command':cmd,'startEpoch':start,'endEpoch':time.time(),'exitStatus':r.returncode})
 (out/f'{n:03d}-stdout.txt').write_bytes(r.stdout);(out/f'{n:03d}-stderr.txt').write_bytes(r.stderr);r.check_returncode();return r.stdout.decode()
def flat(ns):
 rows=[]
 for n in ns:
  if n.get('AXLabel') or n.get('AXUniqueId'):rows.append({k:n.get(k) for k in ['AXLabel','AXUniqueId','AXValue','frame']})
  rows.extend(flat(n.get('children',[])))
 return rows
def rows():return flat(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)))
def capture(name,r):
 events.append({'capture':name,'epoch':time.time()});(out/(name+'-ax.json')).write_text(json.dumps(r,indent=2)+'\n');run('xcrun','simctl','io',uid,'screenshot',out/(name+'.png'))
try:
 env=dict(os.environ,SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='zlagboard.pro',SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID='research.max-hangs')
 if mode=='landscape':env['SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE']='1'
 else:env.pop('SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE',None)
 run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env);run('xcrun','simctl','openurl',uid,'hangten://plan/research.max-hangs/workout')
 deadline=time.monotonic()+100;opened=False;active=False;rest=False;nextactive=False
 while time.monotonic()<deadline:
  r=rows();labels=[x['AXLabel'] or '' for x in r]
  if 'Open' in labels:
   capture('open-confirmation-'+str(len(events)),r);run('/opt/homebrew/bin/axe','tap','--label','Open','--tap-style','physical','--udid',uid);opened=True;continue
  if not active and any('STEP 1 OF' in x for x in labels) and any(x in ['00:05','00:04','00:03'] for x in labels):capture('active-settled',r);active=True
  if active and not rest and any('STEP 2 OF' in x for x in labels):
   capture('following-rest',r);time.sleep(3);capture('following-rest-settled',rows());rest=True
   run('/opt/homebrew/bin/axe','tap','--id','workout.skipStep','--tap-style','physical','--udid',uid);events.append({'uiAction':'Skip step 2 after settled rest capture','epoch':time.time()})
   for n,delay in enumerate([1,2,2]):
    time.sleep(delay);events.append({'capture':'next-active-timed-'+str(n),'epoch':time.time()});run('xcrun','simctl','io',uid,'screenshot',out/('next-active-timed-'+str(n)+'.png'))
   capture('after-next-active-series',rows());nextactive=True;break
  if rest and any('STEP 3 OF' in x for x in labels) and any(x in ['00:05','00:04','00:03'] for x in labels):capture('next-active-settled',r);nextactive=True;break
  time.sleep(.25)
 results={'planID':'research.max-hangs','mode':mode,'activeStateCaptured':active,'followingRestCaptured':rest,'nextActiveTimedSeriesCaptured':nextactive,'routine':'Existing bundled routine unchanged; Rest skipped via visible UI only after settled preview capture','visualHighlightReview':'Timed next-active images require visible Hang timer and red bilateral surfaces; AX may describe a later state. Inspect all screenshots before claiming red/blue/red.'};print(json.dumps(results,indent=2))
except Exception:
 (out/'failure.txt').write_text(traceback.format_exc());raise
finally:(out/'validation.json').write_text(json.dumps({'results':results,'events':events,'commands':commands},indent=2)+'\n')
