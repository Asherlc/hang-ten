from pathlib import Path
import sys,json,hashlib
p=Path(sys.argv[1]);read=lambda name:json.loads((p/name).read_text())
release=read('runtime-release.json');commands=read('commands.json');copy=read('trace-copy.json');end=read('observation-end.json');env=read('launch-review-environment.json');binary=read('installed-binary-gate.json');readiness=read('train-startup-readiness.json')
raws=[f.read_bytes() for f in sorted(p.glob('events-*.jsonl'))];rows=[json.loads(l) for raw in raws for l in raw.splitlines(keepends=True) if l.endswith(b'\n')]
appears=[r for r in rows if r['event']=='workout-probe-appear-before-autostart'];schema=release['markerSchema'];assert schema['reviewed'] is True
anchor=read('appearance-anchor.json') if (p/'appearance-anchor.json').exists() else None
target=anchor['endEpoch'] if anchor else None
inside=[r for r in rows if target is not None and anchor['record']['epoch']<=r['epoch']<=target]
markers=[r for r in inside if r['event'] in schema['events']]
errors=[]
for r in markers:
 missing=[k for k in schema['events'][r['event']]['requiredFields'] if k not in r]
 if missing:errors.append(dict(sequence=r['sequence'],missing=missing))
# Span definitions are supplied only after actual source schema review, never inferred from names.
spans=[]
for definition in schema.get('spans',[]):
 pending={}
 for r in markers:
  if r['event'] not in [definition['beginEvent'],definition['endEvent']]:continue
  key=tuple(r.get(k) for k in definition['identityFields'])
  if r['event']==definition['beginEvent']:
   if key in pending:errors.append(dict(sequence=r['sequence'],error='duplicate unclosed span',key=key))
   pending[key]=r
  else:
   before=pending.pop(key,None)
   spans.append(dict(identity=key,begin=before,end=r,leftCensored=before is None,rightCensored=False))
 for key,r in pending.items():spans.append(dict(identity=key,begin=r,end=None,rightCensored=True,censorEpoch=target))
expected=json.loads(Path(release['priorActionEnvironmentPath']).read_text());expected['HANGTEN_REVIEW_DIAGNOSTIC_RUN']='placid-badger-cad-second-half-startup-observation-action';expected['HANGTEN_REVIEW_STARTUP_OBSERVATION']='1'
checks=dict(exactEnvironment=env==expected,binaryBound=binary['sha256']==release['binarySHA256'],completeJSONL=bool(raws) and all(raw.endswith(b'\n') for raw in raws),completeContiguous=bool(rows) and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)),traceCopiesExact=all(hashlib.sha256(Path(x['copy']).read_bytes()).hexdigest()==x['sha256'] for x in copy['copies']),trainReadiness=readiness['passed'],exactlyOneAppearance=len(appears)==1,appearanceTimely=anchor is not None and not anchor['observedAfterArrivalDeadline'],fixedAnchor=anchor is not None and abs(anchor['endEpoch']-anchor['record']['epoch']-30)<1e-6,markerSchema=not errors,requiredMarkersPresent=all(any(r['event']==e for r in markers) for e in schema['requiredEvents']),recordedEveryCommandInterval=all('startEpoch' in c and 'endEpoch' in c and c['endEpoch']>=c['startEpoch'] for c in commands),noColorPrerequisite=True)
report=dict(checks=checks,markerSchemaErrors=errors,markers=markers,spans=spans,commands=commands,windowEnd=end,recordsAfterFixedWindow=[r['sequence'] for r in rows if target is not None and r['epoch']>target],observationComplete=end['reason']=='fixed-appearance-plus30',limits=['A right-censored span is unfinished within this observation window, not a deadlock or proof it never completes.','Scalar markers and API call spans do not prove GPU rendering, main-thread blockage, or exact visible hand lifetimes.','External polling while the initial screenshot executes is an observation-method change from the prior synchronous capture helper.','Cleanup and final-copy tail can occur after the fixed endpoint and are not additional observation time.','No full12 capture, color, or action-isolation claim is made.'])
out=p/'startup-observation-validation.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(checks,indent=2));assert all(checks.values())
