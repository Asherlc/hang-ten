from pathlib import Path
import os,sys,json,time,subprocess,hashlib,traceback,math
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
name=sys.argv[1];arm=sys.argv[2];assert arm in ['E','F','G']
out=base/name;out.mkdir(exist_ok=False);uid='BDCA0D77-94C2-4A97-900B-443F75C64691';commands=[];captures=[]
def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];i=len(commands);start=time.time()
 try:r=subprocess.run(cmd,capture_output=True,env=env,timeout=20)
 except subprocess.TimeoutExpired as e:
  (out/f'{i:03d}-stdout.txt').write_bytes(e.stdout or b'');(out/f'{i:03d}-stderr.txt').write_bytes(e.stderr or b'');commands.append({'command':cmd,'startEpoch':start,'endEpoch':time.time(),'timeout':True});raise
 (out/f'{i:03d}-stdout.txt').write_bytes(r.stdout);(out/f'{i:03d}-stderr.txt').write_bytes(r.stderr);commands.append({'command':cmd,'startEpoch':start,'endEpoch':time.time(),'exitStatus':r.returncode});r.check_returncode();return r.stdout.decode().strip()
def readrows(folder):
 rows=[]
 for f in folder.glob('events-*.jsonl'):
  for line in f.read_bytes().splitlines(keepends=True):
   if line.endswith(b'\n'):rows.append(json.loads(line))
 return rows
try:
 data=Path(run('xcrun','simctl','get_app_container',uid,'com.hangten.training','data'))
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')}
 flags={'HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC':'1','HANGTEN_REVIEW_DIAGNOSTIC_RUN':'placid-badger-cad-second-half-'+name,'HANGTEN_REVIEW_LANDSCAPE':'1'}
 if arm=='preflight':flags.update(HANGTEN_REVIEW_BOARD_ID='zlagboard.evo',HANGTEN_REVIEW_PLAN_ID='research.max-hangs')
 else:
  frozen=json.loads((base/'standalone-workout-viewport.json').read_text());w,h=frozen['viewportPoints'];assert math.isfinite(w) and math.isfinite(h) and w>0 and h>0
  flags.update(HANGTEN_REVIEW_STANDALONE_BOARD='1',HANGTEN_REVIEW_STANDALONE_WIDTH=repr(w),HANGTEN_REVIEW_STANDALONE_HEIGHT=repr(h))
  flags['HANGTEN_REVIEW_STANDALONE_DRIVER']=arm
 env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()});(out/'launch-review-environment.json').write_text(json.dumps(flags,indent=2)+'\n')
 tracefolder=data/'Documents'/('HighlightDiagnostic-'+flags['HANGTEN_REVIEW_DIAGNOSTIC_RUN']);assert not tracefolder.exists()
 run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env)
 if arm=='preflight':run('xcrun','simctl','openurl',uid,'hangten://plan/research.max-hangs/workout')
 deadline=time.monotonic()+35;schedule=None;selection=None
 while time.monotonic()<deadline:
  rows=readrows(tracefolder)
  if arm=='preflight':
   candidates=[r for r in rows if r.get('selectedIDs')==['edge-20-left','edge-20-right'] and r.get('viewportPoints') and r.get('event')=='sample']
   if len(candidates)>=2:
    selection=candidates[-1];assert candidates[-2]['viewportPoints']==selection['viewportPoints'];break
  else:
   bad=[r for r in rows if r['event'] in ['standalone-readiness-timeout','standalone-viewport-invalid','standalone-script-cancelled','standalone-driver-invalid']];assert not bad,bad
   candidates=[r for r in rows if r['event']=='standalone-schedule']
   if candidates:schedule=candidates[-1];break
  time.sleep(.1)
 if arm=='preflight':
  assert selection,'No stable selected workout viewport'
  record={'viewportPoints':selection['viewportPoints'],'sourceRecord':selection,'sourceRun':name,'method':'Actual GeometryReader viewport logged by same binary; no pixels or AX rounding'}
  dest=base/'standalone-workout-viewport.json';assert not dest.exists();dest.write_text(json.dumps(record,indent=2)+'\n')
 else:
  assert schedule,'No standalone schedule';initial=[410,410*120/700] if arm in ['F','G'] else [w,h];assert schedule['actualViewportPoints']==initial;assert schedule['configuredViewportPoints']==initial
  (out/'schedule.json').write_text(json.dumps(schedule,indent=2)+'\n');assert time.time()<schedule['baseEpoch'],'Schedule discovered late'
  for i,phase in enumerate(schedule['phases']):
   for offset in schedule['captureOffsets']:
    target=schedule['baseEpoch']+i*8+offset;remaining=target-time.time()
    if remaining>0:time.sleep(remaining)
    filename=f'phase-{i}-{phase}-plus-{offset:g}.png';start=time.time();run('xcrun','simctl','io',uid,'screenshot',out/filename);end=time.time();captures.append({'path':str(out/filename),'targetEpoch':target,'startEpoch':start,'endEpoch':end,'phase':phase,'phaseIndex':i,'offset':offset,'sha256':hashlib.sha256((out/filename).read_bytes()).hexdigest()})
  remaining=schedule['baseEpoch']+40-time.time()
  if remaining>0:time.sleep(remaining)
 rows=readrows(tracefolder)
 copies=[]
 for f in tracefolder.glob('events-*.jsonl'):
  target=out/f.name;target.write_bytes(f.read_bytes());copies.append({'source':str(f),'copy':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
 assert rows and all(r['complete'] for r in rows);assert [r['sequence'] for r in rows]==list(range(1,len(rows)+1))
 (out/'trace-copy.json').write_text(json.dumps({'copies':copies,'records':len(rows),'completeContiguous':True},indent=2)+'\n');print(json.dumps({'run':name,'arm':arm,'records':len(rows),'captures':len(captures),'viewport':selection['viewportPoints'] if selection else schedule['actualViewportPoints']}))
except Exception:
 (out/'failure.txt').write_text(traceback.format_exc());raise
finally:
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
