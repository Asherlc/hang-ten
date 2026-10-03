from pathlib import Path
import json,sys,hashlib
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=base/sys.argv[1]
f=next(p.glob('events-*.jsonl'));rows=[json.loads(l) for l in f.read_text().splitlines()];trans=json.loads((p/'transition-observations.json').read_text());token=trans[0]['actualMutation']['sceneLifecycleToken'];caps=json.loads((p/'captures.json').read_text());history=[];pre=[];first=None;other=[]
for r in rows:
 if r.get('sceneLifecycleToken') and r['sceneLifecycleToken']!=token: other.append(r)
 if r.get('sceneLifecycleToken')!=token or 'applicationCensus' not in r or 'boardRenderMembership' not in r:continue
 m=r['boardRenderMembership'];placements=[v for s in r['applicationCensus']['windowScenes'] for w in s['windows'] for v in w.get('rendererPlacements',[])];matches=[v for v in placements if v.get('realitySceneID')==m.get('rootRealitySceneID')];hosts=[v for v in matches if v.get('class')=='RealityKit.ARView']
 if first is None and len(hosts)==1:first=r['sequence']
 x=dict(sequence=r['sequence'],epoch=r['epoch'],event=r['event'],membership=m,hosts=hosts,allMatchingScenePlacements=matches,viewport=r.get('viewportPoints'),rootTransform=r.get('rootTransform'),cameraTransform=r.get('cameraTransform'))
 (pre if first is None else history).append(x)
checks=dict(workoutSceneFromCountdown=any(r.get('sceneLifecycleToken')==token and r['event']=='highlight-after' and r.get('cachedIDs')==[] and r['sequence']<trans[0]['actualMutation']['sequence'] for r in rows),hostObserved=bool(history),everyPostAttachmentCensusExactlyOneIntendedARView=all(len(x['hosts'])==len(x['allMatchingScenePlacements'])==1 for x in history),sameHost= len({v['viewID'] for x in history for v in x['hosts']})==1,sameActualScene=len({x['membership']['rootRealitySceneID'] for x in history})==1,rootCameraActiveSameScene=all(x['membership']['rootActive'] and x['membership']['cameraActive'] and x['membership']['rootRealitySceneID']==x['membership']['cameraRealitySceneID'] for x in history),hostVisible=all(not v['hidden'] and v['alpha']==1 for x in history for v in x['hosts']))
frames=[x['hosts'][0]['frameInWindow'] for x in history if len(x['hosts'])==1];A=frames[0];B=frames[-1];axis=max(range(4),key=lambda i:abs(B[i]-A[i]));obs=[]
for x in history:
 if len(x['hosts'])!=1:continue
 frame=x['hosts'][0]['frameInWindow'];lam=(frame[axis]-A[axis])/(B[axis]-A[axis]) if A!=B else 0;res=max(abs(frame[i]-(A[i]+lam*(B[i]-A[i]))) for i in range(4));obs.append(dict(sequence=x['sequence'],epoch=x['epoch'],frame=frame,progress=lam,residual=res))
checks['sampledFramesOnMonotoneOwnEndpointPath']=all(-1e-8<=x['progress']<=1+1e-8 and x['residual']<=1e-5 for x in obs) and all(y['progress']>=x['progress'] for x,y in zip(obs,obs[1:]))
checks['allPostFirstCaptureCensusesFinal']=all(x['frame']==B for x in obs if x['epoch']>caps[0]['endEpoch'])
r=dict(checks=checks,workoutSceneLifecycleToken=token,traceSHA256=hashlib.sha256(f.read_bytes()).hexdigest(),preUIKitAttachment=pre,postAttachmentCensusCount=len(history),history=history,otherSceneHistory=other,otherSceneTokens=sorted({x['sceneLifecycleToken'] for x in other}),normalOwnEndpoints=[A,B],frameObservations=obs,limitations=['No unobserved frame or initial screenshot settled claim; normal endpoints are measured from UIKit metadata, never image pixels.','Other Train/preworkout scene records retained in full; all-hand lifetime/camera checks cover entire opening stream.'])
out=p/'normal-host-frame-validation.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(checks=checks,censuses=len(history),otherScenes=r['otherSceneTokens'],endpoints=[A,B]),indent=2));assert all(checks.values())
