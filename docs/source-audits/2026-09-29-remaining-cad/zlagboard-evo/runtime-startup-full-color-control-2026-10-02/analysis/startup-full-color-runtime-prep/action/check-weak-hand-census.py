from pathlib import Path
import json,hashlib,uuid
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=E/'startup-full-color-action-landscape'
files=list(p.glob('events-*.jsonl'));assert len(files)==1
raw=files[0].read_bytes();rows=[json.loads(l) for l in raw.splitlines()];caps=json.loads((p/'captures.json').read_text());env=json.loads((p/'launch-review-environment.json').read_text())
ctors={};configs={};views={};dead=set();snapshots=[];errors=[];events=[]
def require(value,label,seq):
 if not value:errors.append(dict(sequence=seq,problem=label))
def token(value,seq):
 try:uuid.UUID(value)
 except (ValueError,TypeError,AttributeError):require(False,'invalid UUID',seq)
for r in rows:
 seq=r['sequence'];event=r['event']
 if event=='hand-lifecycle':
  t=r.get('handLifetimeToken');token(t,seq);kind=r['handKind'];life=r['lifecycleEvent'];events.append(r)
  if life=='constructor-entry':
   require(t not in ctors,'duplicate constructor UUID',seq);ctors[t]=r
  elif life=='make-entry':
   c=ctors.get(t);require(c is not None,'make before constructor',seq)
   if c:require(all(r[k]==c[k] for k in ['handKind','handRootID','handCameraID']),'make entity/kind mismatch',seq)
   v=r.get('viewToken');token(v,seq);views.setdefault(v,dict(tokens=set(),last=None))['tokens'].add(t)
  else:require(False,'unknown hand lifecycle',seq)
 elif event=='hand-camera':
  t=r.get('handLifetimeToken');c=ctors.get(t);require(c is not None,'camera before constructor',seq);events.append(r)
  if c:require(r['handKind']==c['handKind'] and r['handCameraID']==c['handCameraID'],'camera identity mismatch',seq)
  if r['cameraEvent']=='configured':
   require(t not in configs,'duplicate configuration UUID',seq);configs[t]=r
  elif r['cameraEvent']=='reset-fitted':require(t in configs,'fit before configuration',seq)
  else:require(False,'unknown camera event',seq)
 elif event=='hand-view-lifecycle':
  v=r['viewToken'];token(v,seq);entry=views.setdefault(v,dict(tokens=set(),last=None));require(r['swiftUIEvent'] in ['appeared','disappeared'],'unknown SwiftUI event',seq)
  require(set(r['knownLifetimeTokens'])==entry['tokens'],'view known lifetime list differs from actual makes',seq);entry['last']=r;events.append(r)
 if 'boardRenderMembership' in r:
  require('handLifetimeCensus' in r,'missing census at existing board checkpoint',seq)
 if 'handLifetimeCensus' not in r:continue
 census=r['handLifetimeCensus'];tokens=[x['handLifetimeToken'] for x in census]
 require(len(tokens)==len(set(tokens)) and set(tokens)==set(ctors),'census missing constructor tombstone or unknown/duplicate UUID',seq)
 for x in census:
  t=x['handLifetimeToken'];c=ctors.get(t)
  if c is None:continue
  require(x['kind']==c['handKind'] and x['constructedRootID']==c['handRootID'] and x['constructedCameraID']==c['handCameraID'],'census constructed identity mismatch',seq)
  require(x['registrationIssue']=='nil','source registration issue',seq);require(x['configuredObserved']==(t in configs),'configuration observed mismatch',seq)
  for part,key in [('root','handRootID'),('camera','handCameraID')]:
   obj=x[part];require(isinstance(obj.get('alive'),bool),'alive flag missing',seq)
   if obj['alive']:
    require((t,part) not in dead,'weak object revived after dead tombstone',seq);require(obj['entityID']==c[key],'living original identity mismatch',seq)
    require(all(k in obj for k in ['parentEntityID','realitySceneID','enabled','isActive','orthographicComponent','perspectiveComponent']),'missing live entity fields',seq)
    if part=='camera' and t in configs:require(obj['orthographicComponent'] and not obj['perspectiveComponent'],'unexpected camera component',seq)
   else:
    dead.add((t,part));require(set(obj)=={'alive'},'dead object has invented fields',seq)
  expectedViews={v for v,q in views.items() if t in q['tokens']};actualViews=[v['viewToken'] for v in x['viewObservations']]
  require(len(actualViews)==len(set(actualViews)) and set(actualViews)==expectedViews,'view association census mismatch',seq)
  for v in x['viewObservations']:
   q=views.get(v['viewToken'])
   if q is None:continue
   require(set(v['allAssociatedLifetimeTokens'])==q['tokens'],'view lifetime associations lost',seq);last=q['last']
   require(v['lastSwiftUIEvent']==(last['swiftUIEvent'] if last else 'unobserved'),'last appearance event mismatch',seq)
   require(v['lastSwiftUIEventSequence']==(last['sequence'] if last else None),'last appearance sequence mismatch',seq)
 snapshots.append(dict(sequence=seq,epoch=r['epoch'],event=event,boardSceneToken=r.get('sceneLifecycleToken'),lifetimes=census))
brackets=[]
for c in caps:
 before=[s for s in snapshots if s['epoch']<=c['startEpoch']];after=[s for s in snapshots if s['epoch']>=c['endEpoch']]
 brackets.append(dict(image=c['path'],startEpoch=c['startEpoch'],endEpoch=c['endEpoch'],before=before[-1] if before else None,after=after[0] if after else None))
checks=dict(completeContiguous=bool(rows) and raw.endswith(b'\n') and rows[0]['event']=='recorder-open' and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)) and not any(r.get('eventLimitReached') for r in rows),censusGateEnabled=env.get('HANGTEN_REVIEW_HAND_LIFETIME_CENSUS')=='1',realHandsEnabled='HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS' not in env,actualConstructorsObserved=bool(ctors),allConstructedCamerasConfigured=set(configs)==set(ctors),allSchemaIdentityTombstoneAssociationsValid=not errors,all12HaveExistingCensusBrackets=len(brackets)==12 and all(x['before'] and x['after'] for x in brackets))
report=dict(checks=checks,traceSHA256=hashlib.sha256(raw).hexdigest(),errors=errors,constructorCount=len(ctors),constructorRecords=list(ctors.values()),lifecycleAndCameraEvents=events,snapshots=snapshots,captureBrackets=brackets,limitations=['No fixed constructor count, overlap, alive/attached or last-appearance outcome is required.','All UUID lifetimes remain separate even if pointer strings are reused.','Weak liveness and last SwiftUI event are point observations; not actual presenting UIKit host, GPU work, or exact deallocation evidence.','Snapshots come from existing board checkpoints only. Brackets may span time; no claim of hand state at every instant.','Source bookkeeping can perturb timing; failure reproduction judged independently from whole images.'])
out=p/'weak-hand-census-validation.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,errors=errors,constructors=len(ctors),snapshots=len(snapshots)),indent=2));assert all(checks.values())
