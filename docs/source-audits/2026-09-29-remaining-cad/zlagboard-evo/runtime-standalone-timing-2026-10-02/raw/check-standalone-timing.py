from pathlib import Path
import sys,json,hashlib
p=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')/sys.argv[1]
rs=[json.loads(l) for f in p.glob('events-*.jsonl') for l in f.read_text().splitlines()];schedule=json.loads((p/'schedule.json').read_text());base=schedule['baseEpoch'];measured=[r for r in rs if r['epoch']>=base];scenes=[r for r in measured if 'boardRenderMembership'in r];census=[r['applicationCensus'] for r in measured if 'applicationCensus'in r];env=json.loads((p/'launch-review-environment.json').read_text());counter=env.get('HANGTEN_REVIEW_SCENE_UPDATE_COUNTER')=='1'
checks={'oneMakeWholeRun':sum(r['event']=='view-make' for r in rs)==1,'oneScene':len({r['sceneLifecycleToken'] for r in scenes})==1,'oneView':len({r['viewToken'] for r in scenes if 'viewToken'in r})==1,'stableViewportDuringMeasurement':all(r['viewportPoints']==[210,36] for r in scenes if 'viewportPoints'in r),'appActiveDuringMeasurement':all(c['applicationState']==0 for c in census),'windowActiveDuringMeasurement':all(any(s['activationState']==0 and any(w['key'] and not w['hidden'] and w['alpha']==1 for w in s['windows']) for s in c['windowScenes']) for c in census),'rootAndCameraActive':all(r['boardRenderMembership']['rootActive'] and r['boardRenderMembership']['cameraActive'] for r in scenes),'noPeriodicSampler':not any(r['event']=='sample' for r in rs),'noSecondHost':not any('secondHost'in r for r in rs),'counterPresenceCorrect':all(('sceneUpdateCount'in r)==counter for r in scenes),'scriptComplete':any(r['event']=='standalone-script-complete' for r in rs)}
brackets=[]
for c in json.loads((p/'captures.json').read_text()):
 pre=[r for r in scenes if r['epoch']<=c['startEpoch']];post=[r for r in scenes if r['epoch']>=c['endEpoch']];before=pre[-1] if pre else None;after=post[0] if post else None
 expected='preview' if c['phase']=='preview' else 'active';ids=[] if c['phase']=='clear' else ['edge-20-left','edge-20-right']
 valid=before is not None and after is not None and all(r['cachedMode']==expected and r['selectedIDs']==ids and (not ids or (len(r['surfaces'])==2 and all(s['resolvedRGBAValid'] and s['enabled'] and s['attached'] and s['underRegisteredRoot'] and (s['rgba'][2]>s['rgba'][0] if expected=='preview' else s['rgba'][0]>s['rgba'][2]) for s in r['surfaces']))) for r in [before,after])
 brackets.append(dict(c,bracketPassed=valid,priorRecord=before,afterRecord=after,startDelayFromTarget=c['startEpoch']-c['targetEpoch']))
checks['all20Brackets']=len(brackets)==20 and all(c['bracketPassed'] for c in brackets)

snapshots=[r for r in measured if r['event'].startswith('standalone-snapshot-')]
placements=[]
for r in snapshots:
 hosts=[v for s in r['applicationCensus']['windowScenes'] for w in s['windows'] for v in w['rendererPlacements'] if v.get('realitySceneID')==r['boardRenderMembership']['rootRealitySceneID']]
 placements.append({'sequence':r['sequence'],'hosts':hosts})
checks['expected40Snapshots']=len(snapshots)==sum(map(len,schedule['snapshotOffsets']))==40
checks['exactlyOnePublicARView']=all(sum(v['class']=='RealityKit.ARView' for s in r['applicationCensus']['windowScenes'] for w in s['windows'] for v in w['rendererPlacements'])==1 for r in snapshots)
checks['fixedActualPlacement']=all(len(x['hosts'])==1 and x['hosts'][0]['frameInWindow']==[332,166,210,36] and not x['hosts'][0]['hidden'] and x['hosts'][0]['alpha']==1 for x in placements)
checks['singleActualSceneRootCamera']=all(len({r['boardRenderMembership'][k] for r in scenes})==1 for k in ['rootRealitySceneID','cameraRealitySceneID','rootEntityID','cameraEntityID']) and all(r['boardRenderMembership']['rootRealitySceneID']==r['boardRenderMembership']['cameraRealitySceneID'] for r in scenes)
checks['stableTransforms']=all(len({tuple(r[k]) for r in scenes})==1 for k in ['rootTransform','cameraTransform'])
checks['resolvedInputsMatch']=all(r.get('resolvedSurfaceInputs')=={'boardID':'zlagboard.evo','presentationID':'primary','positionID':'primary','isDisplayOnly':False,'ids':r['cachedIDs'],'mode':r['cachedMode']} for r in snapshots)
checks['completeContiguousJSONL']=all(r['complete'] for r in rs) and [r['sequence'] for r in rs]==list(range(1,len(rs)+1))
checks['completeTailAfterCaptures']=all(any(r['event']==e and r['epoch']>max(c['endEpoch'] for c in brackets) for r in rs) for e in ['standalone-timing-tail','standalone-script-complete','standalone-observation-end'])
intended=[r for r in rs if r['event'].startswith('standalone-intended-')]
checks['fiveIntendedPhases']=len(intended)==5 and [r['event'] for r in intended]==[f'standalone-intended-{i}' for i in range(5)]
mutations=[r for r in measured if r['event']=='highlight-after']
checks['fourActualTransitions']=len(mutations)==4 and [(r['cachedMode'],r['cachedIDs']) for r in mutations]==[(mode,['edge-20-left','edge-20-right']) for mode in ['active','preview','active','preview']]
checks['mutationsInIntendedPhase']=len(mutations)==4 and all(base+schedule['phaseStartOffsets'][i]<=r['epoch']<base+schedule['phaseStartOffsets'][i]+schedule['phaseDurations'][i] for i,r in enumerate(mutations,1))
out={'checks':checks,'measurementBaseEpoch':base,'schedule':schedule,'captures':brackets,'placements':placements,'intendedAndMutationEvents':intended+mutations,'limitations':['Sparse census observes boundaries and first6.75s perphase, not continuous middle of long rest. Screenshot commands are observations; no AX or touches.']}
target=p/'timing-validation.json';assert not target.exists();target.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'checks':checks,'maxScreenshotStartLag':max(c['startDelayFromTarget'] for c in brackets)},indent=2));assert all(checks.values())
