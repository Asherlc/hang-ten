from pathlib import Path
import json,math,hashlib
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=E/'prestart-hand-action-repeat-landscape'
f=list(p.glob('events-*.jsonl'));assert len(f)==1
raw=f[0].read_bytes();rows=[json.loads(x) for x in raw.splitlines()];caps=json.loads((p/'captures.json').read_text());trans=json.loads((p/'transition-observations.json').read_text());work=trans[0]['actualMutation']['sceneLifecycleToken']
metrics=set('realityMakeEntries realityUpdateEntries applySyncEntries applySyncCompletions cameraComponentWrites frameCalls cameraTransformEntries cameraPositionWrites cameraLookAtWrites highlightEntries unchangedHighlightRequests highlightUpdatePasses baselineMaterialWrites clearMaterialWrites highlightMaterialWrites'.split())
errors=[];previous={};snapshots=[]
def req(ok,label,r):
 if not ok:errors.append(dict(sequence=r['sequence'],problem=label))
def audit(key,counts,first,latest,r):
 req(set(counts)==metrics,'metric keys',r)
 prior=previous.get(key)
 for m in metrics:
  n=counts.get(m);req(type(n)==int and n>=0,'nonnegative integer '+m,r)
  if not isinstance(n,int):continue
  if n:
   a,b=first.get(m),latest.get(m);valid=all(isinstance(t,(int,float)) and math.isfinite(t) for t in [a,b])
   req(valid,'finite times '+m,r)
   if valid:req(0<=a<=b<=r['uptime'],'time bounds '+m,r)
  else:req(m not in first and m not in latest,'zero count has time '+m,r)
  if prior:
   req(n>=prior[0][m],'count decreased '+m,r)
   if prior[0][m]:
    req(first.get(m)==prior[1].get(m),'first time changed '+m,r)
    req(latest.get(m,0)>=prior[2].get(m,0),'latest time decreased '+m,r)
    if n==prior[0][m]:req(latest.get(m)==prior[2].get(m),'time changed without count '+m,r)
 req(set(first)==set(latest)=={m for m in metrics if counts.get(m,0)>0},'time key correspondence',r)
 previous[key]=(counts,first,latest)
for r in rows:
 if 'boardRenderMembership' in r:req('syncDeliveryCounters' in r,'missing counters at full checkpoint',r)
 if 'syncDeliveryCounters' not in r:continue
 c=r['syncDeliveryCounters'];s=c['sceneToken'];req(c['version']==2 and s==r['sceneLifecycleToken'],'scene identity/version',r)
 req(c['scopeMismatches']==0,'scope mismatch',r);n=c['sceneTotals'];audit((s,None),n,c['firstUptime'],c['latestUptime'],r)
 depth=c['synchronousScopeDepth'];req(type(depth)==int and depth>=0,'scope depth',r)
 req(n['applySyncEntries']-n['applySyncCompletions']==depth,'entry completion depth balance',r)
 unclassified=n['highlightEntries']-n['unchangedHighlightRequests']-n['highlightUpdatePasses']
 req(unclassified==(1 if r['event']=='highlight-before' else 0),'highlight request classification',r)
 req(c['semanticRevision']==n['highlightUpdatePasses'],'semantic revision',r)
 views=c['views'];ids=[v['viewToken'] for v in views];req(len(ids)==len(set(ids)),'duplicate view token',r)
 for v in views:
  audit((s,v['viewToken']),v['counts'],v['firstUptime'],v['latestUptime'],r)
  vn=v['counts'];req(0<=vn['applySyncEntries']-vn['applySyncCompletions']<=depth,'view sync balance',r)
 for m in metrics:req(sum(v['counts'][m] for v in views)<=n[m],'view attribution exceeds scene '+m,r)
 snapshots.append(dict(sequence=r['sequence'],event=r['event'],epoch=r['epoch'],systemUptime=r['uptime'],sceneToken=s,counters=c))
brackets=[]
for cap in caps:
 before=[s for s in snapshots if s['sceneToken']==work and s['epoch']<=cap['startEpoch']];after=[s for s in snapshots if s['sceneToken']==work and s['epoch']>=cap['endEpoch']]
 a=before[-1] if before else None;b=after[0] if after else None
 brackets.append(dict(image=cap['path'],startEpoch=cap['startEpoch'],endEpoch=cap['endEpoch'],before=a,after=b,bracketSpanSeconds=b['epoch']-a['epoch'] if a and b else None,endpointDeltas={m:b['counters']['sceneTotals'][m]-a['counters']['sceneTotals'][m] for m in metrics} if a and b else None))
checks=dict(completeContiguous=bool(rows) and rows[0]['event']=='recorder-open' and raw.endswith(b'\n') and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)) and not any(r.get('eventLimitReached') for r in rows),openingCountersEnabled=rows[0].get('syncDeliveryCountersEnabled') is True,nonemptySnapshots=bool(snapshots),allScalarIdentityTimeAndBalanceChecks=not errors,all12CaptureBrackets=len(brackets)==12 and all(x['before'] and x['after'] for x in brackets),completedScopesObserved=any(s['sceneToken']==work and s['counters']['synchronousScopeDepth']==0 and s['counters']['sceneTotals']['applySyncCompletions']>0 for s in snapshots))
report=dict(checks=checks,errors=errors,traceSHA256=hashlib.sha256(raw).hexdigest(),snapshots=snapshots,captureBrackets=brackets,limitations=['Counts represent CPU calls/assignments including identical values; not GPU work or presentation.','View attribution is synchronous applySync scope only; scene-only loader/orbit calls remain unattributed.','Nested highlight-before includes one not-yet-classified request; snapshots inside sync retain in-flight depth.','Exact endpoint deltas and times are reported; no continuous activity or state claim through sparse late brackets.'])
out=p/'sync-delivery-counter-validation.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,errors=errors,snapshots=len(snapshots)),indent=2));assert all(checks.values())
