from pathlib import Path
import json,sys,hashlib
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=base/sys.argv[1]
rows=[]
for f in p.glob('events-*.jsonl'):rows.extend(json.loads(x) for x in f.read_bytes().splitlines())
trans=json.loads((p/'transition-observations.json').read_text());caps=json.loads((p/'captures.json').read_text());token=trans[0]['actualMutation']['sceneLifecycleToken'];ids=['edge-20-left','edge-20-right']
cpu=[r for r in rows if r.get('sceneLifecycleToken')==token and r.get('cachedIDs')==ids and r.get('surfaces')]
def valid(r,mode):
 return r.get('cachedMode')==mode and all(s.get('resolvedRGBAValid') and s.get('enabled') and s.get('underRegisteredRoot') and (s['rgba'][0]>s['rgba'][2] if mode=='active' else s['rgba'][2]>s['rgba'][0]) for s in r['surfaces'])
out=[]
for c in caps:
 before=[r for r in cpu if r['epoch']<=c['startEpoch']];after=[r for r in cpu if r['epoch']>=c['endEpoch']];a=before[-1] if before else None;b=after[0] if after else None
 passed=a is not None and b is not None and valid(a,c['mode']) and valid(b,c['mode']) and all(valid(r,c['mode']) for r in cpu if c['startEpoch']<=r['epoch']<=c['endEpoch'])
 out.append(dict(c,cpuBefore=a,cpuAfter=b,cpuExpectedColorBracket=passed))
boundaries=[]
for r in cpu:
 if r['event'] not in ['highlight-before','highlight-after'] or 'applicationCensus' not in r:continue
 c=r['applicationCensus'];placements=[]
 for sc in c['windowScenes']:
  for w in sc['windows']:
   for v in w.get('rendererPlacements',[]):
    if v.get('realitySceneID')==r['boardRenderMembership'].get('rootRealitySceneID'):placements.append(v)
 boundaries.append(dict(sequence=r['sequence'],event=r['event'],epoch=r['epoch'],cachedMode=r['cachedMode'],requestedMode=r['requestedMode'],applicationState=c['applicationState'],windowSceneStates=[x['activationState'] for x in c['windowScenes']],orientations=[x['interfaceOrientation'] for x in c['windowScenes']],boardPlacements=placements,boardRenderMembership=r['boardRenderMembership']))
marker=[r for r in rows if r['event']=='workout-probe-appear-before-autostart']
intervals=[trans[i+1]['actualMutation']['epoch']-trans[i]['actualMutation']['epoch'] for i in range(2)]
checks=dict(completeContiguous=[r['sequence'] for r in rows]==list(range(1,len(rows)+1)) and all(r['complete'] for r in rows),captures12=len(caps)==12,allCPUBrackets=all(r['cpuExpectedColorBracket'] for r in out),sameScene=len({x['actualMutation']['sceneLifecycleToken'] for x in trans})==1,naturalFirstHang=6<intervals[0]<8,naturalRest=179<intervals[1]<181,freshSession=len(marker)==1 and 'pausedElapsed=0.0;activeStartIsNil=true;routineStartedIsNil=true' in marker[0]['state'],boundaryAppActive=all(x['applicationState']==0 for x in boundaries),boundaryWindowActive=all(x['windowSceneStates']==[0] for x in boundaries),boundaryLandscape=all(x['orientations']==[3] for x in boundaries),lateBoundaryCensus=any(x['epoch']>=trans[2]['actualMutation']['epoch'] and x['boardPlacements'] for x in boundaries),noAXOrTouch=not any('axe' in ' '.join(c['command']).lower() for c in json.loads((p/'commands.json').read_text())))
report=dict(checks=checks,traceRecords=len(rows),actualPhaseIntervals=intervals,firstSessionMarker=marker,boundaryCensus=boundaries,captures=out,limitations=['Boundary census is not a fresh census at every screenshot instant','Initial selected material was accepted only after same-scene empty/countdown selection; actual running timers independently require visual review','Direct-root layout/history/containment is a combined intervention; no compensated dimensions','Existing sampler may end before second Hang; final pre-preview mutation brackets late screenshot CPU state'])
(p/'structural-correspondence.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,records=len(rows),intervals=intervals),indent=2))
assert all(checks.values())
