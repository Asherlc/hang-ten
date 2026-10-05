from pathlib import Path
import json,sys,hashlib
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=E/sys.argv[1]
f=next(p.glob('events-*.jsonl'));raw=f.read_bytes();rows=[json.loads(x) for x in raw.splitlines()]
env=json.loads((p/'launch-review-environment.json').read_text());action=env.get('HANGTEN_REVIEW_DETACH_DISAPPEARING_BOARD_HOST')=='1'
trans=json.loads((p/'transition-observations.json').read_text());work=trans[0]['actualMutation']['sceneLifecycleToken'];first=trans[0]['actualMutation']['sequence']
ctors=[r for r in rows if r['event']=='board-scene-constructed'];tokens=[r['sceneLifecycleToken'] for r in ctors];pre=[t for t in tokens if t!=work]
assert len(pre)==1,pre
pre=pre[0];makes=[r for r in rows if r['event']=='view-make'];before=[r for r in rows if r['event']=='detach-trial-before'];after=[r for r in rows if r['event']=='detach-trial-after']
trial=[r for r in rows if 'boardDetachTrial' in r];hosts=[h for r in trial for h in r['boardDetachTrial']['hosts']]
def host(r,t):return [h for h in r['boardDetachTrial']['hosts'] if h['sceneLifecycleToken']==t]
def attached(h):return h['rootParentID']==h['cameraParentID']==h['recordedParentID']!='nil' and h['rootActualSceneID']==h['cameraActualSceneID']==h['recordedActualSceneID']!='nil'
def detached(h):return all(h[k]=='nil' for k in ['rootParentID','cameraParentID','rootActualSceneID','cameraActualSceneID'])
checks=dict(commonTrial=env.get('HANGTEN_REVIEW_BOARD_DETACH_TRIAL')=='1' and env.get('HANGTEN_REVIEW_PREDECESSOR_ATTACHMENT_CENSUS')=='1',normalTrainPresentHandsOff=env.get('HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS')=='1' and 'HANGTEN_REVIEW_SUPPRESS_TRAIN_BOARD_HOST' not in env and 'HANGTEN_REVIEW_WORKOUT_AT_ROOT' not in env,exactTwoConstructorsAndMakes=len(ctors)==2 and len(makes)==2 and sorted(r['sceneLifecycleToken'] for r in makes)==sorted(tokens),oneBeforeAfterTrainOnly=len(before)==len(after)==1 and before[0]['sceneLifecycleToken']==after[0]['sceneLifecycleToken']==pre,actionFlagCorrect=all(r['boardDetachTrial']['detachRequested']==action for r in trial),allHostsRetainedCurrentValid=bool(hosts) and all(h['modelRetainedForTrial'] and h['currentOwner'] and h['invalid']=='nil' and not h['reattachedAfterDetach'] for h in hosts),tagMatchesExactPredecessor=all(h['trainMarked']==(h['sceneLifecycleToken']==pre) for h in hosts),oneStableOwnerPerHost=all(len({h['ownerToken'] for h in hosts if h['sceneLifecycleToken']==t})==1 for t in tokens),beforeOwnershipObserved=len(before)==1 and len(host(before[0],pre))==1 and host(before[0],pre)[0]['attachmentObserved'] and attached(host(before[0],pre)[0]),actionBeforeFirstHang=len(after)==1 and after[0]['sequence']<first)
allowed={'HANGTEN_REVIEW_BOARD_ID','HANGTEN_REVIEW_PLAN_ID','HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC','HANGTEN_REVIEW_DIAGNOSTIC_RUN','HANGTEN_REVIEW_LANDSCAPE','HANGTEN_REVIEW_WORKOUT_BOUNDARY_CENSUS','HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS','HANGTEN_REVIEW_PREDECESSOR_ATTACHMENT_CENSUS','HANGTEN_REVIEW_BOARD_DETACH_TRIAL'}
if action:allowed.add('HANGTEN_REVIEW_DETACH_DISAPPEARING_BOARD_HOST')
structuralAction=p.name=='train-unmount-unmount-landscape'
if structuralAction:allowed.add('HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT')
checks['commonDetachEnabledBothArms']=action
checks['structuralFlagMatchesArm']=(env.get('HANGTEN_REVIEW_UNMOUNT_TRAIN_FOR_WORKOUT')=='1')==structuralAction
checks['exactEnvironmentAllowlist']=set(env)==allowed
post=[r for r in trial if after and r['sequence']>=after[0]['sequence']];current=[r for r in trial if r['sequence']>=first]
checks['postActionEveryTrialHasPredecessor']=bool(post) and all(len(host(r,pre))==1 for r in post)
checks['bothHostsPresentFromFirstHang']=bool(current) and all(len(r['boardDetachTrial']['hosts'])==2 and len(host(r,work))==1 for r in current)
checks['workoutAttachedUnmarkedUnchanged']=bool(current) and all(attached(host(r,work)[0]) and not host(r,work)[0]['detached'] and not host(r,work)[0]['trainMarked'] and not host(r,work)[0]['disappeared'] for r in current)
checks['expectedPredecessorAttachmentThroughout']=bool(post) and all((detached(host(r,pre)[0]) and host(r,pre)[0]['detached']) if action else (attached(host(r,pre)[0]) and not host(r,pre)[0]['detached']) for r in post)
weak=[]
for r in post:
 obs=[x for x in r.get('boardLifetimeCensus',[]) if x['sceneLifecycleToken']==pre];weak.append(dict(sequence=r['sequence'],event=r['event'],epoch=r['epoch'],observations=obs,trial=host(r,pre)))
checks['weakPredecessorAliveEveryPostObservation']=bool(weak) and all(len(x['observations'])==1 and x['observations'][0]['wrapperAlive'] and x['observations'][0]['root']['alive'] and x['observations'][0]['camera']['alive'] for x in weak)
checks['weakMembershipMatchesAction']=all(all(x['observations'][0][e]['parentEntityID']=='nil' and x['observations'][0][e]['realitySceneID']=='nil' and not x['observations'][0][e]['isActive'] for e in ['root','camera']) if action else all(x['observations'][0][e]['parentEntityID']!='nil' and x['observations'][0][e]['realitySceneID']!='nil' and x['observations'][0][e]['isActive'] for e in ['root','camera']) for x in weak)
ct={r['sceneLifecycleToken']:r for r in ctors}
checks['weakEntityIDsPreserved']=all(x['observations'][0][e]['entityID']==ct[pre][e+'ID'] for x in weak for e in ['root','camera'])
tail=json.loads((p/'following-preview-tail.json').read_text())['record'];checks['observationsThroughTail']=bool(post) and post[-1]['sequence']>=tail['sequence']
report=dict(checks=checks,action=action,predecessorToken=pre,workoutToken=work,traceSHA256=hashlib.sha256(raw).hexdigest(),constructors=ctors,beforeRecords=before,afterRecords=after,postActionPointObservations=weak,postActionCount=len(post),scope='Exact observed ownership and membership; not proof of GPU host destruction or generic lifecycle correctness. Intentional model and lease retention is common to both arms. No callback suppression.')
q=p/'guarded-detach-validation.json';assert not q.exists();q.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,postActionCount=len(post)),indent=2));assert all(checks.values())
