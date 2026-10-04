"""Offline retained-proof validation only. Never creates app/device/build resources."""
from pathlib import Path
import json,sys,subprocess,time,hashlib,signal,traceback
import muted_audio_schema,branch_schema
from clock_stability import audit as audit_clock
from marker_correlations import audit
D=Path(__file__).parent;P=D.parent/'evo/hand-image-muted-workout-live-c-landscape';assert P.is_dir()
# Parent must declare the completed trial frozen before validators write new reports.
gate=Path(sys.argv[1]);g=json.loads(gate.read_text());assert g['completedRunFrozen'] and g['arm']==P.name
for x in g['frozenFiles']:assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256']
results=[];active=None
signal.signal(signal.SIGINT,lambda n,f:(_ for _ in ()).throw(InterruptedError('SIGINT')))
signal.signal(signal.SIGTERM,lambda n,f:(_ for _ in ()).throw(InterruptedError('SIGTERM')))
helpers=['check-cpu-semantics.py','check-frames.py','check-constructors.py','check-ownership.py','check-navigation.py','check-real-hands.py','check-weak-hand-census.py','check-sync-counters.py','check-muted-current-hands.py']
for n in helpers:
 args=[P.name] if n in helpers[:3] else []
 record=dict(helper=n,command=['rtk','proxy','python3',str(D/'live'/n),*args],startEpoch=time.time(),limitSeconds=20)
 with (P/(n+'.stdout')).open('xb') as out,(P/(n+'.stderr')).open('xb') as err:
  try:
   active=subprocess.Popen(record['command'],stdout=out,stderr=err);record['pid']=active.pid;active.wait(timeout=20)
  except BaseException:record['error']=traceback.format_exc()
  finally:
   if active is not None and active.poll() is None:
    active.terminate()
    try:active.wait(timeout=.5)
    except subprocess.TimeoutExpired:active.kill();active.wait(timeout=1)
   record.update(exitStatus=active.returncode if active else None,endEpoch=time.time());active=None;results.append(record)
   # Distinct newly written validator status; original capture completion stays untouched.
   (P/'muted-validator-command-results.json').write_text(json.dumps(results,indent=2)+'\n')
  if 'error' in record:break
rows=[json.loads(l) for f in P.glob('events-*.jsonl') for l in f.read_bytes().splitlines()];checks={};reports={}
for label,fn in [('audio',lambda:muted_audio_schema.validate(rows,final=True)),('startup',lambda:audit(rows,json.loads((D/'marker-schema.json').read_text()),None)),('branch',lambda:branch_schema.protocol(rows,'live'))]:
 try:
  reports[label]=fn();checks[label]=not reports[label].get('errors',[])
 except BaseException:reports[label]=dict(error=traceback.format_exc());checks[label]=False
caps=json.loads((P/'captures.json').read_text());checks['exact12']=len(caps)==12;checks['deadlines']=bool(caps) and all(0<=c['startEpoch']-c['targetEpoch']<=.150 for c in caps);checks['noMissedSequence']=not (P/'missed-capture.json').exists() and not (P/'missing-initial-sequence.json').exists();checks['tail']=(P/'following-preview-tail.json').exists();checks['cleanup']=json.loads((P/'app-cleanup.json').read_text())['passed'] is True
commands=json.loads((P/'commands.json').read_text());launch=[c for c in commands if c['command'][:4]==['rtk','proxy','xcrun','simctl'] and 'launch' in c['command']];checks['exactMutedLaunch']=len(launch)==1 and launch[0]['command'][-2:]==['-workoutAudioCuesEnabled','NO']
checks['allHelpers']=len(results)==len(helpers) and all(x['exitStatus']==0 and 'error' not in x for x in results)
clock=audit_clock(rows,commands,caps,json.loads((P/'transition-observations.json').read_text()));reports['clockStability']=clock;checks['clockStability']=clock['passed']
clockPath=P/'prospective-clock-stability.json';assert not clockPath.exists();clockPath.write_text(json.dumps(clock,indent=2)+'\n')
for c in caps:checks['imageHash:'+Path(c['path']).name]=hashlib.sha256(Path(c['path']).read_bytes()).hexdigest()==c['sha256']
report=dict(checks=checks,reports=reports,passed=all(checks.values()),visualResult='REQUIRES_SEPARATE_WHOLE_IMAGE_REVIEW',oldPrestartAndSupplemental='NOT_APPLICABLE_AS_MUTED_GATE; ORIGINAL_BYTES_RETAINED',limit='Technical proof only, no repair/acceptance or IMAGE authorization')
p=P/'muted-independent-validation.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,passed=report['passed']),indent=2));assert report['passed']
