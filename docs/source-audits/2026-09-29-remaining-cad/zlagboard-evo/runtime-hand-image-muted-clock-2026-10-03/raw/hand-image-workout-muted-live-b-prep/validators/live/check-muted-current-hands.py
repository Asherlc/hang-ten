from pathlib import Path
import json,hashlib
P=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo/hand-image-muted-workout-live-b-landscape')
read=lambda n:json.loads((P/n).read_text())
files=list(P.glob('events-*.jsonl'));assert len(files)==1
raw=files[0].read_bytes();rows=[json.loads(x) for x in raw.splitlines()];bySeq={r['sequence']:r for r in rows};env=read('launch-review-environment.json');weak=read('weak-hand-census-validation.json');hands=read('real-hand-lifetime-camera-validation.json');caps=read('captures.json');errors=[]
def req(ok,label):
 if not ok:errors.append(label)
def parse(r):return dict(x.split('=',1) for x in r['state'].split(';'))
marks=[(r,parse(r)) for r in rows if r['event']=='workout-prestart-hand-state'];appear=[(r,parse(r)) for r in rows if r['event']=='workout-probe-appear-before-autostart'];values=[s.get('countdown') for r,s in marks]
req(values in [['0','3','2','1','0'],['3','2','1','0']],'Exact initial countdown callbacks')
req(len(appear)==1,'One workout appearance')
req(all(s.get('flag')=='false' and s.get('suppressed')=='false' for r,s in marks),'False prestart flags throughout')
req(all(s.get('prestartHandFlag')=='false' and s.get('prestartHandsSuppressed')=='false' for r,s in appear),'False appearance flags')
req(any(s.get('routineStartedIsNil')=='true' for r,s in marks+appear),'Initial not-started observation')
started=[r for r,s in marks if s.get('routineStartedIsNil')=='false'];req(bool(started),'Started state observed')
if started:req(not any(s.get('routineStartedIsNil')=='true' and r['sequence']>started[0]['sequence'] for r,s in marks),'No later reset')
req(any(s.get('routineStartedIsNil')=='false' and s.get('countdown')=='3' for r,s in marks),'Started positive countdown')
req(any(s.get('routineStartedIsNil')=='false' and s.get('countdown')=='0' for r,s in marks),'Started zero countdown')
req(all(k not in env for k in ['HANGTEN_REVIEW_SUPPRESS_PRESTART_HAND_HOSTS','HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS','HANGTEN_REVIEW_ALL_HAND_PERSPECTIVE','HANGTEN_REVIEW_HAND_IMAGE']),'LIVE unsuppressed orthographic environment')
req(env.get('HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT')=='1','Ordinary Train-unmount gate')
req(all(weak['checks'].values()) and all(hands['checks'].values()),'Original weak and camera gates')
req(len(caps)==12 and len(weak['captureBrackets'])==12,'All12 existing brackets')
points=[];tokens=[]
for b,c in zip(weak['captureBrackets'],caps):
 req(b['image']==c['path'] and b['startEpoch']==c['startEpoch'] and b['endEpoch']==c['endEpoch'],'Exact capture provenance')
 for side in ['before','after']:
  q=b[side];req(q is not None,'Existing '+side+' census')
  if q is None:continue
  r=bySeq.get(q['sequence']);req(r is not None and r.get('handLifetimeCensus')==q['lifetimes'] and r['epoch']==q['epoch'],'Exact raw census provenance')
  live=[]
  for h in q['lifetimes']:
   if h['kind']!='pair':continue
   a,z=h['root'],h['camera']
   if all(x.get('alive') and x.get('enabled') and x.get('isActive') and x.get('parentEntityID') not in (None,'nil') and x.get('realitySceneID') not in (None,'nil') for x in (a,z)) and a['realitySceneID']==z['realitySceneID']:live.append(h)
  firstBefore=(len(points)==0 and side=='before')
  req(len(live)==1 or (firstBefore and len(live)==0),'Exactly one observed active attached pair, except prospective first-before gap, at '+Path(c['path']).name+' '+side)
  token=live[0]['handLifetimeToken'] if len(live)==1 else None;tokens.append(token);points.append(dict(image=c['path'],side=side,snapshot=q,attachedPairToken=token))
current=next((t for t in tokens if t is not None),None);incompleteFirst=bool(tokens) and tokens[0] is None
req(len(tokens)==24 and current is not None and all(t==current for t in tokens[1:]) and tokens[0] in (None,current),'Same current hand token at remaining23 points; only first-before may be pending')
ctors=[r for r in rows if r['event']=='hand-lifecycle' and r['lifecycleEvent']=='constructor-entry'];makes=[r for r in rows if r['event']=='hand-lifecycle' and r['lifecycleEvent']=='make-entry'];curctors=[r for r in ctors if r['handLifetimeToken']==current];curmakes=[r for r in makes if r['handLifetimeToken']==current]
req(bool(ctors) and all(r['handKind']=='pair' for r in ctors),'Actual landscape pair path only, no fixed count')
req(len(curctors)==len(curmakes)==1,'Unique current constructor/make identity')
if curctors and curmakes and caps:req(curctors[0]['sequence']<curmakes[0]['sequence'] and all(r['epoch']<caps[0]['startEpoch'] for r in curctors+curmakes),'Current ctor/make before actual first screenshot')
if incompleteFirst and curctors and curmakes and caps:
 beforePoint=points[0]['snapshot'];afterPoint=points[1]['snapshot']
 fit=[r for r in rows if r.get('event')=='hand-camera' and r.get('cameraEvent')=='reset-fitted' and r.get('handLifetimeToken')==current and r['epoch']<caps[0]['startEpoch']]
 req(beforePoint['sequence']<curctors[0]['sequence'] and beforePoint['epoch']<curctors[0]['epoch'],'First-before census strictly predates current construction')
 req(not any(h['handLifetimeToken']==current for h in beforePoint['lifetimes']),'First-before is missing observation, not contrary current state')
 req(bool(fit) and curmakes[0]['sequence']<fit[-1]['sequence'] and fit[-1]['orthographicPresent'] and not fit[-1]['perspectivePresent'] and fit[-1]['allDepthsFinite'] and fit[-1]['allDepthsInsideUnchangedClips'],'Current valid camera fit before actual first screenshot')
 req(afterPoint['epoch']>=caps[0]['endEpoch'],'First-after census follows screenshot end')
 req(not any(r.get('event')=='hand-view-lifecycle' and r.get('swiftUIEvent')=='disappeared' and current in r.get('knownLifetimeTokens',[]) and curmakes[0]['sequence']<r['sequence']<afterPoint['sequence'] for r in rows),'No disappearance between current make and first-after')
 req(points[1]['attachedPairToken']==current,'First-after must actually observe current attached pair')
checks=dict(completeStream=raw.endswith(b'\n') and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)),prospectiveMutedCurrentHandCriteria=not errors)
report=dict(checks=checks,errors=errors,criterion='PROSPECTIVE_AUDIO_OFF_FIRST_BEFORE_GAP_QUALIFIED',incompleteFirstOwnershipBracket=incompleteFirst,requiredAttachedPointCount=sum(t==current for t in tokens),traceSHA256=hashlib.sha256(raw).hexdigest(),currentLifetimeToken=current,allConstructorRecords=ctors,allMakeRecords=makes,currentConstructor=curctors,currentMake=curmakes,predicateMarkers=[dict(record=r,state=s) for r,s in marks],capturePoints=points,limits=['No fixed two-host history or prewarm/arm ordering imposed. Other lifetimes retained descriptively.','Only a pre-constructor first-before gap is qualified; current ctor/make/fit must precede actual screenshot and first-after plus remaining23 points must observe attached current pair. This is not24-point proof.','No continuous lifetime, rendered-pixel, GPU or causal claim. Whole images require separate review.'])
out=P/'muted-current-hand-validation.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,errors=errors,actualConstructors=len(ctors)),indent=2));assert all(checks.values())
