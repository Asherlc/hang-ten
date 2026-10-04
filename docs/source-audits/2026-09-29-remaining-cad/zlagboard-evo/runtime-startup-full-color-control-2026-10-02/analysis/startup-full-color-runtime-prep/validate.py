from pathlib import Path
import sys,subprocess,json,hashlib
from marker_correlations import audit
D=Path(__file__).parent;E=D.parent/'evo';role=sys.argv[1];assert role in ['control','action'];p=E/('startup-full-color-'+role+'-landscape');results=[]
for name in ['check-cpu-semantics.py','check-frames.py','check-constructors.py','check-ownership.py','check-navigation.py','check-real-hands.py','check-weak-hand-census.py','check-sync-counters.py','check-prestart-hands.py']:
 args=[p.name] if name in ['check-cpu-semantics.py','check-frames.py','check-constructors.py'] else []
 r=subprocess.run(['rtk','proxy','python3',str(D/role/name),*args],capture_output=True)
 for suffix,raw in [('stdout',r.stdout),('stderr',r.stderr)]:
  f=p/(name+'.'+suffix);assert not f.exists();f.write_bytes(raw)
 results.append(dict(helper=name,exitStatus=r.returncode))
# Original prestart status remains untouched; separate common amended timing audit.
r=subprocess.run(['rtk','proxy','python3',str(D/'check-supplemental-timing.py'),role],capture_output=True)
(p/'supplemental-timing.stdout').write_bytes(r.stdout);(p/'supplemental-timing.stderr').write_bytes(r.stderr);results.append(dict(helper='check-supplemental-timing.py',exitStatus=r.returncode))
if role=='action':
 r=subprocess.run(['rtk','proxy','python3',str(D/role/'compare.py')],capture_output=True);(p/'compare.stdout').write_bytes(r.stdout);(p/'compare.stderr').write_bytes(r.stderr);results.append(dict(helper='compare.py',exitStatus=r.returncode))
rows=[json.loads(l) for f in p.glob('events-*.jsonl') for l in f.read_bytes().splitlines()];schema=json.loads((D/'marker-schema.json').read_text());correlation=audit(rows,schema,None);(p/'startup-correlation-validation.json').write_text(json.dumps(correlation,indent=2)+'\n')
caps=json.loads((p/'captures.json').read_text());schedule=dict(exact12=len(caps)==12,allStartsWithin150ms=bool(caps) and all(0<=c['startEpoch']-c['targetEpoch']<=.150 for c in caps),noMissedWindow=not (p/'missed-capture.json').exists(),noMissingInitialSequence=not (p/'missing-initial-sequence.json').exists())
(p/'capture-schedule-validation.json').write_text(json.dumps(schedule,indent=2)+'\n');(p/'validator-command-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(commands=results,schedule=schedule,startupCorrelationErrors=correlation['errors']),indent=2))
# Original prestart failure is never relabeled; root gates using both original and separate supplement.
assert all(x['exitStatus']==0 for x in results if x['helper']!='check-prestart-hands.py') and not correlation['errors'] and all(schedule.values())
