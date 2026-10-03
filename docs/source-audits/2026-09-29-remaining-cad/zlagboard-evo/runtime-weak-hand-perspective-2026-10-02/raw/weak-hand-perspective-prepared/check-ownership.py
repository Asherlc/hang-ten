from pathlib import Path
import json,sys,hashlib
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
arm='weak-hand-perspective'
p=E/'weak-hand-perspective-landscape';retained=False
files=list(p.glob('events-*.jsonl'));assert len(files)==1
raw=files[0].read_bytes();rows=[json.loads(x) for x in raw.splitlines()]
read=lambda n:json.loads((p/n).read_text())
env=read('launch-review-environment.json');release=read('runtime-release.json')
trans=read('transition-observations.json');assert len(trans)==3
work=trans[0]['actualMutation']['sceneLifecycleToken'];first=trans[0]['actualMutation']['sequence']
ctors=[r for r in rows if r['event']=='board-scene-constructed'];tokens=[r['sceneLifecycleToken'] for r in ctors]
assert len(tokens)==len(set(tokens))==2 and tokens.count(work)==1
pre=next(t for t in tokens if t!=work);ct={r['sceneLifecycleToken']:r for r in ctors}
makes=[r for r in rows if r['event']=='view-make'];before=[r for r in rows if r['event']=='detach-trial-before'];after=[r for r in rows if r['event']=='detach-trial-after']
trial=[r for r in rows if 'boardDetachTrial' in r];hosts=[h for r in trial for h in r['boardDetachTrial']['hosts']]
def host(r,t):return [h for h in r['boardDetachTrial']['hosts'] if h['sceneLifecycleToken']==t]
def attached(h):return h['rootParentID']==h['cameraParentID']==h['recordedParentID']!='nil' and h['rootActualSceneID']==h['cameraActualSceneID']==h['recordedActualSceneID']!='nil'
def detached(h):return all(h[k]=='nil' for k in ['rootParentID','cameraParentID','rootActualSceneID','cameraActualSceneID'])
allowed={'HANGTEN_REVIEW_BOARD_ID','HANGTEN_REVIEW_PLAN_ID','HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC','HANGTEN_REVIEW_DIAGNOSTIC_RUN','HANGTEN_REVIEW_LANDSCAPE','HANGTEN_REVIEW_WORKOUT_BOUNDARY_CENSUS','HANGTEN_REVIEW_PREDECESSOR_ATTACHMENT_CENSUS','HANGTEN_REVIEW_BOARD_HOST_OBSERVATION','HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT','HANGTEN_REVIEW_HAND_LIFETIME_CENSUS','HANGTEN_REVIEW_ALL_HAND_PERSPECTIVE'}
if retained:allowed|={'HANGTEN_REVIEW_BOARD_DETACH_TRIAL','HANGTEN_REVIEW_DETACH_DISAPPEARING_BOARD_HOST'}
readiness=read('train-startup-readiness.json');ready=readiness['evidence'];readyHost=ready['host'];readyParent=readyHost['recordedParentID'];readyScene=readyHost['recordedActualSceneID']
bySeq={r['sequence']:r for r in rows}
readyExact=(readiness['passed'] and readiness['boundSeconds']==20 and readiness['elapsedSeconds']<=20.1 and ready['trainToken']==pre and bySeq.get(ready['makeRecord']['sequence'])==ready['makeRecord'] and bySeq.get(ready['attachmentRecord']['sequence'])==ready['attachmentRecord'] and readyHost['trainMarked'] and readyHost['currentOwner'] and readyHost['invalid']=='nil' and not readyHost['detached'] and not readyHost['disappeared'] and readyHost['attachmentObserved'] and attached(readyHost) and all(readyHost[k] for k in ['modelAlive','rootAlive','cameraAlive']) and readyHost['modelRetainedForTrial'] is retained and ready['weak']['wrapperAlive'] and all(ready['weak'][e]['alive'] and ready['weak'][e]['isActive'] and ready['weak'][e]['parentEntityID']==readyParent and ready['weak'][e]['realitySceneID']==readyScene for e in ['root','camera']))
def ordinaryNaturalLoss(h):
 if retained or not readyExact or h['sceneLifecycleToken']!=pre or h['invalid']!='attachment-changed-before-disappear':return False
 fields=['rootParentID','cameraParentID','rootActualSceneID','cameraActualSceneID']
 expected=[readyParent,readyParent,readyScene,readyScene]
 return (h['ownerToken']==readyHost['ownerToken'] and h['currentOwner'] and not h['detached'] and not h['modelRetainedForTrial'] and any(h[k]=='nil' for k in fields) and all(h[k] in ['nil',v] for k,v in zip(fields,expected)))
def invalidAllowed(h):return h['invalid']=='nil' or ordinaryNaturalLoss(h)
checks=dict(completeStream=bool(rows) and rows[0]['event']=='recorder-open' and raw.endswith(b'\n') and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)) and not any(r.get('eventLimitReached') for r in rows),exactEnvironmentKeys=set(env)==allowed,exactCommonValues=env.get('HANGTEN_REVIEW_BOARD_ID')=='zlagboard.evo' and env.get('HANGTEN_REVIEW_PLAN_ID')=='research.max-hangs' and all(env[k]=='1' for k in allowed-{'HANGTEN_REVIEW_BOARD_ID','HANGTEN_REVIEW_PLAN_ID','HANGTEN_REVIEW_DIAGNOSTIC_RUN'}),releaseModeMatches=release['arm']==arm and release['retainedDetachIntervention'] is retained,exactRunID=env.get('HANGTEN_REVIEW_DIAGNOSTIC_RUN')=='placid-badger-cad-second-half-weak-hand-perspective',canonicalModelSHA=all(r['modelSHA256']=='9492a6d5a033bf1f11e0d6ac111711f8ea63d5d26226b6b638e72a288ae13eee' for r in ctors),exactTwoConstructorsAndMakes=len(makes)==2 and sorted(r['sceneLifecycleToken'] for r in makes)==sorted(tokens),oneBeforeAfterTrainOnly=len(before)==len(after)==1 and before[0]['sceneLifecycleToken']==after[0]['sceneLifecycleToken']==pre,actionFlagCorrect=bool(trial) and all(r['boardDetachTrial']['detachRequested'] is retained for r in trial),retentionModeCorrect=bool(hosts) and all(h['modelRetainedForTrial'] is retained for h in hosts),allHostsCurrentValid=bool(hosts) and all(h['currentOwner'] and invalidAllowed(h) and not h['reattachedAfterDetach'] for h in hosts),tagMatchesPredecessor=all(h['trainMarked']==(h['sceneLifecycleToken']==pre) for h in hosts),oneStableOwnerPerHost=all(len({h['ownerToken'] for h in hosts if h['sceneLifecycleToken']==t})==1 for t in tokens),exactInitialReadiness=readyExact,beforeOwnershipObservedOrOrdinaryNaturalLoss=len(before)==1 and len(host(before[0],pre))==1 and host(before[0],pre)[0]['attachmentObserved'] and ((attached(host(before[0],pre)[0]) and all(host(before[0],pre)[0][k] for k in ['modelAlive','rootAlive','cameraAlive'])) or ordinaryNaturalLoss(host(before[0],pre)[0])),disappearBeforeFirstHang=len(after)==1 and after[0]['sequence']<first)
assert len(after)==1
post=[r for r in trial if r['sequence']>=after[0]['sequence']];current=[r for r in trial if r['sequence']>=first]
checks['postEveryTrialKeepsPredecessorRecord']=bool(post) and all(len(host(r,pre))==1 for r in post)
checks['bothRecordsFromFirstHang']=bool(current) and all(len(r['boardDetachTrial']['hosts'])==2 and len(host(r,work))==1 for r in current)
checks['workoutAliveAttachedUnchanged']=bool(current) and all(attached(host(r,work)[0]) and all(host(r,work)[0][k] for k in ['modelAlive','rootAlive','cameraAlive']) and not any(host(r,work)[0][k] for k in ['detached','trainMarked','disappeared']) for r in current)
weak=[]
for r in post:
 obs=[x for x in r.get('boardLifetimeCensus',[]) if x['sceneLifecycleToken']==pre]
 weak.append(dict(sequence=r['sequence'],event=r['event'],epoch=r['epoch'],observations=obs,trial=host(r,pre)))
checks['weakCensusRecordAtEveryPostPoint']=bool(weak) and all(len(x['observations'])==1 for x in weak)
assert checks['weakCensusRecordAtEveryPostPoint']
checks['weakIdentityForEveryLivingEntity']=all(not x['observations'][0][e]['alive'] or x['observations'][0][e]['entityID']==ct[pre][e+'ID'] for x in weak for e in ['root','camera'])
checks['predecessorDisappearedThroughout']=all(x['trial'][0]['disappeared'] for x in weak)
if retained:
 checks['retainedObjectsAliveThroughout']=all(all(x['trial'][0][k] for k in ['modelAlive','rootAlive','cameraAlive']) and x['observations'][0]['wrapperAlive'] and all(x['observations'][0][e]['alive'] for e in ['root','camera']) for x in weak)
 checks['guardedDetachSuccessfulThroughout']=all(detached(x['trial'][0]) and x['trial'][0]['detached'] and all(x['observations'][0][e]['parentEntityID']=='nil' and x['observations'][0][e]['realitySceneID']=='nil' and not x['observations'][0][e]['isActive'] for e in ['root','camera']) for x in weak)
else:
 checks['zeroExplicitDetachesEntireStream']=all(not h['detached'] for h in hosts) and all(not r['boardDetachTrial']['detachRequested'] for r in trial)
 checks['zeroIntentionalRetentionEntireStream']=all(not h['modelRetainedForTrial'] for h in hosts)
 checks['noUnexpectedOrdinaryOwnershipTransfer']=all(all(h[k] in ['nil',v] for k,v in zip(['rootParentID','cameraParentID','rootActualSceneID','cameraActualSceneID'],[readyParent,readyParent,readyScene,readyScene])) for r in trial if r['sequence']>=ready['attachmentRecord']['sequence'] for h in host(r,pre))
 # Weak death is permitted, not required and not treated as proof of detachment.
 checks['deadEntitiesHaveNoInventedOwnership']=all(all(x['trial'][0][e+k]=='nil' for k in ['ParentID','ActualSceneID']) for x in weak for e in ['root','camera'] if not x['trial'][0][e+'Alive'])
ordinaryLossRecords=[r for r in trial if any(ordinaryNaturalLoss(h) for h in r['boardDetachTrial']['hosts'])]
tail=read('following-preview-tail.json')['record'];checks['throughTail']=bool(post) and post[-1]['sequence']>=tail['sequence'] and any(r==tail for r in rows)
report=dict(version=1,arm=arm,checks=checks,retainedDetachIntervention=retained,predecessorToken=pre,workoutToken=work,traceSHA256=hashlib.sha256(raw).hexdigest(),constructors=ctors,beforeRecords=before,afterRecords=after,postActionPointObservations=weak,postActionCount=len(post),ordinaryTeardownOrderDifference=bool(ordinaryLossRecords),firstOrdinaryTeardownOrderRecord=ordinaryLossRecords[0] if ordinaryLossRecords else None,ordinaryTeardownOrderSequences=[r['sequence'] for r in ordinaryLossRecords],limitations=['Ordinary weak wrapper/entity death is allowed but not required; nil does not establish explicit detach or backing UIView destruction.','No strong retention is established by source review plus explicit retention mode; raw weak observations alone cannot prove every internal reference.','Prior real-hands and new weak-census runs both request structural removal with ordinary ownership, no intentional retention or explicit detach; new diagnostic bookkeeping and census gate can perturb timing.'])
out=p/'structural-dependency-ownership.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(checks,indent=2));assert all(checks.values())
