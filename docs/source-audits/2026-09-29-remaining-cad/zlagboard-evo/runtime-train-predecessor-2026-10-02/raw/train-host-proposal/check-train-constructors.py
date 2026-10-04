from pathlib import Path
import json,sys,hashlib
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=base/sys.argv[1]
f=next(p.glob('events-*.jsonl'));raw=f.read_bytes();rows=[json.loads(l) for l in raw.splitlines()]
env=json.loads((p/'launch-review-environment.json').read_text());suppressed=env.get('HANGTEN_REVIEW_SUPPRESS_TRAIN_BOARD_HOST')=='1'
trans=json.loads((p/'transition-observations.json').read_text());token=trans[0]['actualMutation']['sceneLifecycleToken']
ctors=[r for r in rows if r['event']=='board-scene-constructed'];tokens=[r['sceneLifecycleToken'] for r in ctors]
makes=[r for r in rows if r['event']=='view-make'];workoutMakes=[r for r in makes if r.get('sceneLifecycleToken')==token]
otherCtors=[r for r in ctors if r['sceneLifecycleToken']!=token]
sceneRows=[r for r in rows if r.get('sceneLifecycleToken')]
placements=[dict(sequence=r['sequence'],epoch=r['epoch'],event=r['event'],recordScene=r.get('sceneLifecycleToken'),placements=[v for s in r['applicationCensus']['windowScenes'] for w in s['windows'] for v in w.get('rendererPlacements',[])]) for r in rows if 'applicationCensus' in r]
checks=dict(completeContiguous=raw.endswith(b'\n') and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)),openingBeforeConstructors=bool(ctors) and ctors[0]['sequence']>rows[0]['sequence'],uniqueConstructorTokens=len(tokens)==len(set(tokens)),exactlyOneWorkoutConstructor=tokens.count(token)==1,exactlyOneWorkoutMake=len(workoutMakes)==1,allSceneRecordsHaveConstructor=all(r['sceneLifecycleToken'] in tokens for r in sceneRows),markerGateMatches=all(r['trainBoardSuppressionRequested']==suppressed for r in ctors),strictHandsEnabled=env.get('HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS')=='1')
if suppressed:
 checks['onlyWorkoutConstructor']=tokens==[token]
 checks['onlyWorkoutMake']=len(makes)==1 and makes[0]['sceneLifecycleToken']==token
else:
 checks['observedPredecessorConstruction']=bool(otherCtors) and all(r['sequence']<trans[0]['actualMutation']['sequence'] for r in otherCtors)
result=dict(checks=checks,suppressed=suppressed,workoutToken=token,constructors=ctors,makes=makes,otherConstructors=otherCtors,allRendererPlacementCensuses=placements,scope='Markers identify completed native board-scene initialization before async USDZ loading, not every possible loader attempt or active rendering. Predecessor placement in history does not alone establish overlapping lifetime. All renderer census rows retained.',traceSHA256=hashlib.sha256(raw).hexdigest())
out=p/'train-constructor-validation.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(checks=checks,constructors=len(ctors),makes=len(makes),otherConstructors=len(otherCtors)),indent=2));assert all(checks.values())
