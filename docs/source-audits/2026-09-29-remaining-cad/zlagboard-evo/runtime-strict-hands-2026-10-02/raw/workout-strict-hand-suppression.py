from pathlib import Path
import os,sys,json,time,subprocess,hashlib,traceback
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
arm=sys.argv[1];assert arm in ['on','off']
out=base/('strict-hands-'+arm+'-landscape');out.mkdir(exist_ok=False)
uid='BDCA0D77-94C2-4A97-900B-443F75C64691';commands=[];captures=[];transitions=[];tracefolder=None
start=time.monotonic();deadline=start+300;pending=[];known=set();scene=None

def run(*args,env=None):
 cmd=['rtk','proxy',*map(str,args)];n=len(commands);t=time.time()
 try:r=subprocess.run(cmd,capture_output=True,env=env,timeout=max(.1,min(20,deadline-time.monotonic())))
 except subprocess.TimeoutExpired as e:
  (out/f'{n:03d}-stdout.txt').write_bytes(e.stdout or b'');(out/f'{n:03d}-stderr.txt').write_bytes(e.stderr or b'');commands.append({'command':cmd,'startEpoch':t,'endEpoch':time.time(),'timeout':True});raise
 (out/f'{n:03d}-stdout.txt').write_bytes(r.stdout);(out/f'{n:03d}-stderr.txt').write_bytes(r.stderr);commands.append({'command':cmd,'startEpoch':t,'endEpoch':time.time(),'exitStatus':r.returncode});r.check_returncode();return r.stdout.decode().strip()

def readrows():
 rows=[]
 for f in tracefolder.glob('events-*.jsonl'):
  for l in f.read_bytes().splitlines(keepends=True):
   if l.endswith(b'\n'):rows.append(json.loads(l))
 return rows

def save_trace():
 copies=[];rs=[]
 if tracefolder:
  for f in tracefolder.glob('events-*.jsonl'):
   raw=f.read_bytes();t=out/f.name;t.write_bytes(raw);copies.append({'source':str(f),'copy':str(t),'sha256':hashlib.sha256(raw).hexdigest()});assert raw.endswith(b'\n');rs.extend(json.loads(l) for l in raw.splitlines())
 if rs:assert all(r['complete'] for r in rs) and [r['sequence'] for r in rs]==list(range(1,len(rs)+1))
 (out/'trace-copy.json').write_text(json.dumps({'copies':copies,'records':len(rs),'completeContiguous':bool(rs),'copiedEpoch':time.time(),'includesSamplerEnd':any(r['event']=='sample-end' for r in rs)},indent=2)+'\n')

try:
 data=Path(run('xcrun','simctl','get_app_container',uid,'com.hangten.training','data'))
 flags={'HANGTEN_REVIEW_BOARD_ID':'zlagboard.evo','HANGTEN_REVIEW_PLAN_ID':'research.max-hangs','HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC':'1','HANGTEN_REVIEW_DIAGNOSTIC_RUN':'placid-badger-cad-second-half-strict-hands-'+arm,'HANGTEN_REVIEW_LANDSCAPE':'1','HANGTEN_REVIEW_WORKOUT_BOUNDARY_CENSUS':'1'}
 flags['HANGTEN_REVIEW_WORKOUT_AT_ROOT']='1'
 if arm=='off':flags['HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS']='1'
 env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')};env.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()})
 (out/'launch-review-environment.json').write_text(json.dumps(flags,indent=2)+'\n')
 (out/'protocol.json').write_text(json.dumps({'hardBoundSeconds':300,'plannedPhases':['active','preview','active'],'captureOffsetsAfterActualMutation':[.25,1,3,5],'afterLaunchUIAccess':'screenshots only; no AX queries/taps/Skip','externalTracePollingSeconds':.03,'routineUnchanged':True,'samplerLimit':'Existing120-iteration sampler remains; new identical both-arm boundary census on actual highlight-before/after supplies sparse late-phase app/window/placement evidence, not every capture instant','arm':arm,'startup':'Existing WorkoutAccessGate and production automatic-start policy in both arms; explicit DEBUG AUTOSTART omitted, fresh process/session; both arms direct root with no openurl; OFF adds only immutable strict all-hand-host suppression flag; old landscape hand-OFF flag absent both arms'},indent=2)+'\n')
 tracefolder=data/'Documents'/('HighlightDiagnostic-'+flags['HANGTEN_REVIEW_DIAGNOSTIC_RUN']);assert not tracefolder.exists()
 run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env)
 initialStart=time.time();run('xcrun','simctl','io',uid,'screenshot',out/'launch-initial.png');initialEnd=time.time()
 (out/'launch-initial-capture.json').write_text(json.dumps(dict(startEpoch=initialStart,endEpoch=initialEnd,sha256=hashlib.sha256((out/'launch-initial.png').read_bytes()).hexdigest()),indent=2)+'\n')
 while time.monotonic()<deadline:
  rs=readrows();observed=time.time()
  for r in rs:
   if r['sequence'] in known:continue
   known.add(r['sequence'])
   if r['event']!='highlight-after' or r.get('cachedIDs')!=['edge-20-left','edge-20-right']:continue
   if scene is None:
    earlierClear=[q for q in rs if q['sequence']<r['sequence'] and q.get('sceneLifecycleToken')==r['sceneLifecycleToken'] and q['event']=='highlight-after' and q.get('cachedIDs')==[]]
    if not earlierClear:
     with (out/'excluded-prestart-candidates.jsonl').open('a') as f:f.write(json.dumps(dict(record=r,reason='No preceding empty/countdown selection on this scene; not labeled running Hang'))+'\n')
     continue
    scene=r['sceneLifecycleToken']
   if r['sceneLifecycleToken']!=scene:continue
   if len(transitions)>=3:continue
   expected=['active','preview','active'][len(transitions)]
   assert r['cachedMode']==expected,('Unexpected phase',r)
   i=len(transitions);transitions.append({'phaseIndex':i,'mode':expected,'actualMutation':r,'hostFirstObservedEpoch':observed,'observationLagSeconds':observed-r['epoch']})
   for offset in [.25,1,3,5]:pending.append({'phaseIndex':i,'mode':expected,'offset':offset,'targetEpoch':r['epoch']+offset})
   (out/'transition-observations.json').write_text(json.dumps(transitions,indent=2)+'\n')
  now=time.time();pending.sort(key=lambda q:q['targetEpoch'])
  if pending and pending[0]['targetEpoch']<=now:
   q=pending.pop(0);name=f"phase-{q['phaseIndex']}-{q['mode']}-plus-{q['offset']:g}.png"
   beforeRows=readrows();beforeObserved=time.time();captureStart=time.time();run('xcrun','simctl','io',uid,'screenshot',out/name);captureEnd=time.time();afterRows=readrows();afterObserved=time.time()
   row=dict(q,path=str(out/name),sha256=hashlib.sha256((out/name).read_bytes()).hexdigest(),startEpoch=captureStart,endEpoch=captureEnd,startDelayFromTarget=captureStart-q['targetEpoch'],traceReadBefore={'observedEpoch':beforeObserved,'lastSequence':beforeRows[-1]['sequence'] if beforeRows else None},traceReadAfter={'observedEpoch':afterObserved,'lastSequence':afterRows[-1]['sequence'] if afterRows else None})
   captures.append(row);(out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
  if len(transitions)==3 and len(captures)==12:
   tail=[r for r in rs if r['event']=='highlight-before' and r.get('sceneLifecycleToken')==scene and r.get('cachedMode')=='active' and r.get('requestedMode')=='preview' and r['epoch']>transitions[2]['actualMutation']['epoch']]
   if tail and time.time()>tail[-1]['epoch']+.5:
    (out/'following-preview-tail.json').write_text(json.dumps(dict(record=tail[-1],hostObservedEpoch=time.time()),indent=2)+'\n');break
  time.sleep(.03)
 assert len(transitions)==3 and len(captures)==12 and (out/'following-preview-tail.json').exists(),'Hard bound reached before all required transitions/captures/following-preview tail'
 save_trace();print(json.dumps({'phases':len(transitions),'captures':len(captures),'elapsedSeconds':time.monotonic()-start,'run':str(out)}))
except Exception:
 (out/'failure.txt').write_text(traceback.format_exc());save_trace();raise
finally:
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(out/'captures.json').write_text(json.dumps(captures,indent=2)+'\n')
