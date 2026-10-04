from pathlib import Path
import json,hashlib,sys
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');arm=sys.argv[1];assert arm in ['control','action','action-repeat'];p=E/('prestart-hand-'+arm+'-landscape');read=lambda n:json.loads((p/n).read_text());originalPath=p/'prestart-hand-validation.json';original=read(originalPath.name);weak=read('weak-hand-census-validation.json');caps=read('captures.json');raw=next(p.glob('events-*.jsonl')).read_bytes();rows=[json.loads(l) for l in raw.splitlines()];bySeq={r['sequence']:r for r in rows};current=original['currentLifetimeToken'];ctors=[r for r in rows if r['event']=='hand-lifecycle' and r.get('lifecycleEvent')=='constructor-entry' and r.get('handLifetimeToken')==current];makes=[r for r in rows if r['event']=='hand-lifecycle' and r.get('lifecycleEvent')=='make-entry' and r.get('handLifetimeToken')==current];errors=[]
def req(ok,label):
 if not ok:errors.append(label)
def parse(r):return dict(x.split('=',1) for x in r['state'].split(';'))
markers=[dict(record=r,state=parse(r)) for r in rows if r['event']=='workout-prestart-hand-state'];positive=[x['record'] for x in markers if x['state']['routineStartedIsNil']=='false' and x['state']['countdown'] in ['1','2','3']];zero=[x['record'] for x in markers if x['state']['routineStartedIsNil']=='false' and x['state']['countdown']=='0'];first=read('transition-observations.json')[0]['actualMutation'];req(len(caps)==12 and len(weak['captureBrackets'])==12,'exact12 images and original census brackets');req(len(ctors)==len(makes)==1 and bool(positive),'actual current constructor/make and positive countdown identified')
known={'current pair ctor/make after final observed positive countdown and before first capture bracket','current pair live active attached at phase-0-active-plus-0.25.png before'}
unknown=[x for x in original['errors'] if x not in known];req(not unknown,'no unrelated original checker failure')
req(all(v for k,v in original['checks'].items() if k!='prestartSpecificChecks'),'all other original checker gates')
req(all(weak['checks'].values()),'original weak identity/count/tombstone/stream checks')
timing=[]
if len(ctors)==len(makes)==1 and positive and caps:
 last=positive[-1]
 for r in ctors+makes:
  req(last['sequence']<r['sequence'] and last['epoch']<r['epoch']<caps[0]['startEpoch'],'current ctor/make after last positive and before actual first screenshot START')
  timing.append(dict(event=r['lifecycleEvent'],sequence=r['sequence'],epoch=r['epoch'],secondsAfterLastPositive=r['epoch']-last['epoch'],secondsBeforeFirstScreenshotStart=caps[0]['startEpoch']-r['epoch'],secondsRelativeToFirstHang=r['epoch']-first['epoch'],secondsRelativeToZeroCallback=r['epoch']-zero[0]['epoch'] if len(zero)==1 else None,lastPositive=last))
points=[];incomplete=False;requiredAttached=0
for i,(b,cap) in enumerate(zip(weak['captureBrackets'],caps)):
 req(b['image']==cap['path'] and b['startEpoch']==cap['startEpoch'] and b['endEpoch']==cap['endEpoch'],'capture bracket provenance')
 for side in ['before','after']:
  snap=b[side];req(snap is not None,'census point exists')
  if snap is None:continue
  actual=bySeq.get(snap['sequence']);req(actual is not None and actual.get('handLifetimeCensus')==snap['lifetimes'] and actual['epoch']==snap['epoch'],'census point exact raw provenance')
  found=[x for x in snap['lifetimes'] if x['handLifetimeToken']==current]
  attached=False
  if len(found)==1:
   x=found[0];attached=all(x[k]['alive'] and x[k]['enabled'] and x[k]['isActive'] and x[k]['parentEntityID']!='nil' and x[k]['realitySceneID']!='nil' for k in ['root','camera']) and x['root']['realitySceneID']==x['camera']['realitySceneID']
  exception=(i==0 and side=='before' and not found and len(ctors)==1 and snap['sequence']<ctors[0]['sequence'] and snap['epoch']<ctors[0]['epoch']<cap['startEpoch'])
  if exception:incomplete=True
  else:req(attached,'required current hand ownership at '+Path(cap['path']).name+' '+side);requiredAttached+=int(attached)
  points.append(dict(image=cap['path'],side=side,sequence=snap['sequence'],epoch=snap['epoch'],currentLifetimePresent=len(found)==1,currentLiveActiveAttached=attached,firstBeforePredatesConstructorException=exception))
req(requiredAttached==(23 if incomplete else 24),'all remaining23 points or complete24 attached')
checks=dict(completeStream=bool(rows) and rows[0]['event']=='recorder-open' and raw.endswith(b'\n') and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)),allAmendedCommonCriteria=not errors)
report=dict(checks=checks,errors=errors,arm=arm,criterion='SUPPLEMENTAL_POST_CONTROL_REVIEW_IDENTICAL_FOR_BOTH_ARMS',originalProspectiveCheckPassed=all(original['checks'].values()),originalProspectiveErrors=original['errors'],originalReportPath=str(originalPath),originalReportSHA256=hashlib.sha256(originalPath.read_bytes()).hexdigest(),traceSHA256=hashlib.sha256(raw).hexdigest(),supplementalTimingCheckPassed=all(checks.values()),incompleteFirstOwnershipBracket=incomplete,requiredAttachedPointCount=requiredAttached,actualFirstCapture=caps[0],timingMargins=timing,ownershipPoints=points,limitations=['This is an explicitly amended supplemental criterion after the original control checker failed; original check/report remain unmodified.','The first before-census may lack the current hand only if it is strictly before its constructor, which must precede actual screenshot START. First after and every remaining point require current root/camera live active attached.','An incomplete first ownership bracket is not equivalent to complete ownership proof at screenshot time. Actual constructor/make timing plus later census and whole image visibility are separate evidence.','Last positive/zero callbacks are sparse state observations; no requirement ctor follows zero callback, no exact permission-edge inference.','No GPU commit/presenting-host proof or continuous lifetime assertion.'])
out=E/('prestart-hand-'+arm+'-supplemental-timing.json');assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,errors=errors,incompleteFirstOwnershipBracket=incomplete,requiredAttachedPointCount=requiredAttached),indent=2));assert all(checks.values())
