from pathlib import Path
import sys,json
p=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')/sys.argv[1]
rows=[json.loads(line) for f in p.glob('events-*.jsonl') for line in f.read_text().splitlines()]
schedule=json.loads((p/'schedule.json').read_text());base=schedule['baseEpoch']
snapshots=[r for r in rows if r['event'].startswith('standalone-snapshot-') and r['epoch']>=base]
placements=[];checks={};inputs=[]
for r in snapshots:
 scene=r['boardRenderMembership']['rootRealitySceneID']
 hosts=[v for s in r['applicationCensus']['windowScenes'] for w in s['windows'] for v in w['rendererPlacements'] if v.get('realitySceneID')==scene]
 placements.append({'sequence':r['sequence'],'epoch':r['epoch'],'hosts':hosts})
 i=r.get('resolvedSurfaceInputs');inputs.append({'sequence':r['sequence'],'epoch':r['epoch'],'inputs':i,'cachedMode':r['cachedMode'],'cachedIDs':r['cachedIDs']})
checks['41SparseSnapshots']=len(snapshots)==41
checks['exactlyOneMatchedHost']=all(len(r['hosts'])==1 for r in placements)
rects=[r['hosts'][0]['frameInWindow'] for r in placements if len(r['hosts'])==1]
initialRects=[r['hosts'][0]['frameInWindow'] for r in placements if len(r['hosts'])==1 and r['epoch']<base+8]
settledRects=[r['hosts'][0]['frameInWindow'] for r in placements if len(r['hosts'])==1 and r['epoch']>=base+9]
checks['stableInitialLeafPlacement']=bool(initialRects) and len({tuple(r) for r in initialRects})==1
checks['stableSettledLeafPlacement']=bool(settledRects) and len({tuple(r) for r in settledRects})==1
checks['settledLeaf210x36']=bool(settledRects) and all(r[2:]==[210,36] for r in settledRects)
checks['resolvedInputsPresent']=all(r['inputs'] is not None for r in inputs)
checks['resolvedInputsMatchCPU']=all(r['inputs'] and r['inputs']['ids']==r['cachedIDs'] and r['inputs']['mode']==r['cachedMode'] for r in inputs)
checks['resolvedBoardPresentationAndInteraction']=all(r['inputs'] and r['inputs']['boardID']=='zlagboard.evo' and r['inputs']['presentationID']=='primary' and r['inputs']['isDisplayOnly']==False for r in inputs)
positions=sorted({r['inputs']['positionID'] for r in inputs if r['inputs']})
checks['oneResolvedPositionAllPhases']=len(positions)==1
out={'checks':checks,'initialLeafRect':initialRects[0] if initialRects else None,'settledLeafRect':settledRects[0] if settledRects else None,'actualIntermediateWidthSamples':[r for r in placements if len(r['hosts'])==1 and 210<r['hosts'][0]['frameInWindow'][2]<410],'resolvedPositions':positions,'placements':placements,'inputs':inputs,'surfaceInputEvents':[r for r in rows if r['event']=='surface-inputs']}
target=p/'surface-placement-validation.json';assert not target.exists();target.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['checks','initialLeafRect','settledLeafRect','resolvedPositions','actualIntermediateWidthSamples']},indent=2));assert all(checks.values())
