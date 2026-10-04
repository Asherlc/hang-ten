from pathlib import Path
import json,hashlib
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');arm='control';action=False;p=E/('prestart-hand-'+arm+'-landscape')
f=list(p.glob('events-*.jsonl'));assert len(f)==1;raw=f[0].read_bytes();rows=[json.loads(l) for l in raw.splitlines()];read=lambda n:json.loads((p/n).read_text());env=read('launch-review-environment.json');trans=read('transition-observations.json');weak=read('weak-hand-census-validation.json');hands=read('real-hand-lifetime-camera-validation.json')
def state(r):return dict(x.split('=',1) for x in r['state'].split(';'))
marks=[dict(record=r,parsed=state(r)) for r in rows if r['event']=='workout-prestart-hand-state'];appear=[dict(record=r,parsed=state(r)) for r in rows if r['event']=='workout-probe-appear-before-autostart'];ctors=weak['constructorRecords'];makes=[r for r in rows if r['event']=='hand-lifecycle' and r['lifecycleEvent']=='make-entry'];nil=[x for x in marks if x['parsed'].get('routineStartedIsNil')=='true'];allowed=[x for x in marks if x['parsed'].get('routineStartedIsNil')=='false'];firstHang=trans[0]['actualMutation'];errors=[]
def require(ok,label):
 if not ok:errors.append(label)
require(bool(marks) and len(marks)<=5,'bounded initial countdown records (at most initial plus3/2/1/0)')
require(len(appear)==1,'exactly one workout appear marker')
require(bool(nil) and bool(allowed),'observed initial prestart and later started predicate')
require(all(x['parsed'].get('flag')==str(action).lower() and x['parsed'].get('suppressed')==str(action and x['parsed'].get('routineStartedIsNil')=='true').lower() for x in marks),'predicate flags match requested arm')
require(all(x['parsed'].get('prestartHandFlag')==str(action).lower() and x['parsed'].get('prestartHandsSuppressed')==str(action and x['parsed'].get('routineStartedIsNil')=='true').lower() for x in appear),'appear flags match requested arm')
require(all(x['parsed'].get('countdown') in ['0','1','2','3'] for x in marks),'unchanged countdown values')
require(any(x['parsed'].get('countdown')=='3' and x['parsed'].get('routineStartedIsNil')=='false' for x in marks),'started countdown observed')
require(any(x['parsed'].get('countdown')=='0' and x['parsed'].get('routineStartedIsNil')=='false' for x in marks),'started countdown expiry observed')
require(not any(x['parsed'].get('routineStartedIsNil')=='true' and x['record']['sequence']>allowed[0]['record']['sequence'] for x in marks) if allowed else False,'no reset/cancellation in passive run')
require(env.get('HANGTEN_REVIEW_SUPPRESS_PRESTART_HAND_HOSTS')==('1' if action else None),'action flag exact')
require('HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS' not in env and 'HANGTEN_REVIEW_ALL_HAND_PERSPECTIVE' not in env,'actual hands enabled orthographic')
require(all(c['handKind']=='pair' for c in ctors),'only expected landscape pair path constructed')
require(len(ctors)==len(makes)==(1 if action else 2),'expected actual constructor and make lifetimes for arm')
# Point states are not permission-edge timestamps. Newly allowed child evaluation may precede false callback.
if action:
 require(all(all(v==0 for v in x['record']['handLifecycleCounts'].values()) for x in nil+ [x for x in appear if x['parsed'].get('routineStartedIsNil')=='true']),'zero constructor/make counts at every observed suppressed-prestart state')
 current=ctors[0]['handLifetimeToken'] if len(ctors)==1 else None
else:
 early=ctors[0]['handLifetimeToken'] if len(ctors)==2 else None;current=ctors[-1]['handLifetimeToken'] if len(ctors)==2 else None
 require(bool(early) and ctors[0]['sequence']<firstHang['sequence'],'earlier constructor before genuine firstHang')
 require(any(m['handLifetimeToken']==early and m['sequence']<firstHang['sequence'] for m in makes),'earlier make before genuine firstHang')
 require(any(r['event']=='hand-view-lifecycle' and r.get('swiftUIEvent')=='disappeared' and early in r.get('knownLifetimeTokens',[]) and r['sequence']<firstHang['sequence'] for r in rows),'earlier view disappearance before genuine firstHang')
 require(all(any(x['handLifetimeToken']==early and not x['root']['alive'] and not x['camera']['alive'] for x in b[k]['lifetimes']) for b in weak['captureBrackets'] for k in ['before','after']),'earlier hand dead at all captured phase brackets')
require(current is not None,'current lifetime identified')
points=[]
for b in weak['captureBrackets']:
 pair={}
 for k in ['before','after']:
  matches=[x for x in b[k]['lifetimes'] if x['handLifetimeToken']==current];ok=len(matches)==1
  if ok:
   x=matches[0];ok=all(x[z]['alive'] and x[z]['enabled'] and x[z]['isActive'] and x[z]['parentEntityID']!='nil' and x[z]['realitySceneID']!='nil' for z in ['root','camera']) and x['root']['realitySceneID']==x['camera']['realitySceneID']
  require(ok,'current pair live active attached at '+Path(b['image']).name+' '+k);pair[k]=dict(sequence=b[k]['sequence'],epoch=b[k]['epoch'],matches=matches)
 points.append(dict(image=b['image'],**pair))
checks=dict(completeStream=bool(rows) and rows[0]['event']=='recorder-open' and raw.endswith(b'\n') and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)),existingWeakAndCameraChecksPass=all(weak['checks'].values()) and all(hands['checks'].values()),prestartSpecificChecks=not errors,all12Bracketed=len(points)==12)
report=dict(checks=checks,errors=errors,arm=arm,traceSHA256=hashlib.sha256(raw).hexdigest(),predicateMarkers=marks,appearanceMarkers=appear,constructorRecords=ctors,makeRecords=makes,currentLifetimeToken=current,capturePointEvidence=points,zeroObservedSuppressedPrestartConstructorsAndMakes=(action and not errors),startupFirstHandHistoryReproduced=(not action and not errors),limitations=['Application predicate differs from object lifetime. Source gate plus complete constructor stream and exact lifetime audit support scoped suppression; sparse callbacks do not locate the exact permission edge.','No constructor is required to follow the later false-state callback: SwiftUI may evaluate allowed children first.','Control earlier-life history is identified by constructor/make/disappearance/dead observations; its exact identity branch is not directly logged.','No prestart screenshot or clear-slot UIKit measurement is added. Clear-slot preservation is source-derived; actual workout board endpoints/path are independently validated.','Actual visible hands and board colors require separate whole-image review; counters and weak refs are not presentation/GPU evidence.'])
out=p/'prestart-hand-validation.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,errors=errors,actualConstructors=len(ctors)),indent=2));assert all(checks.values())
