from pathlib import Path
import json,hashlib,math
p=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo/startup-full-color-action-landscape')
files=list(p.glob('events-*.jsonl'));assert len(files)==1
raw=files[0].read_bytes();rows=[json.loads(l) for l in raw.splitlines()]
env=json.loads((p/'launch-review-environment.json').read_text());caps=json.loads((p/'captures.json').read_text());tail=json.loads((p/'following-preview-tail.json').read_text())['record']
keys=['single.constructor-entry','single.make-entry','pair.constructor-entry','pair.make-entry']
expected=dict.fromkeys(keys,0);countsExact=True;constructors=[];makeLinks=[];configs=[];fits=[];unknown=[]
# Correlate sparse synchronous constructor/configuration order, not object lifetime.
for r in rows:
 if r['event']=='hand-lifecycle':
  key=r['handKind']+'.'+r['lifecycleEvent']
  if key not in expected:unknown.append(r);continue
  expected[key]+=1
  if r['lifecycleEvent']=='constructor-entry':constructors.append(r)
  else:
   candidates=[x for x in constructors if x['handKind']==r['handKind'] and x['handRootID']==r['handRootID'] and x['sequence']<r['sequence']]
   makeLinks.append(dict(make=r,constructor=candidates[-1] if candidates else None))
 if r.get('handLifecycleCounts')!=expected:countsExact=False
 if r['event']=='hand-camera':
  if r['cameraEvent']=='configured':
   candidates=[x for x in constructors if x['handKind']==r['handKind'] and x['sequence']<r['sequence']]
   configs.append(dict(config=r,constructor=candidates[-1] if candidates else None))
  elif r['cameraEvent']=='reset-fitted':
   candidates=[x for x in configs if x['config']['handKind']==r['handKind'] and x['config']['handCameraID']==r['handCameraID'] and x['config']['sequence']<r['sequence']]
   fits.append(dict(fit=r,configuration=candidates[-1] if candidates else None))
  else:unknown.append(r)
cameraRows=[r for r in rows if r['event']=='hand-camera']
made={x['constructor']['sequence'] for x in makeLinks if x['constructor']}
fitted={x['configuration']['constructor']['sequence'] for x in fits if x['configuration'] and x['configuration']['constructor']}
checks=dict(completeStream=bool(rows) and rows[0]['event']=='recorder-open' and raw.endswith(b'\n') and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)) and not any(r.get('eventLimitReached') for r in rows),handSuppressionAbsent='HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS' not in env and rows[0]['suppressesAllHandHosts'] is False,perspectiveExperimentAbsent='HANGTEN_REVIEW_ALL_HAND_PERSPECTIVE' not in env and rows[0]['usesPerspectiveHandCameras'] is False,instrumentationVersion=rows[0]['handLifecycleInstrumentationVersion']==1,exactCountsMatchEventsAtEveryRecord=countsExact,actualCreatedAndMadePath=bool(constructors) and bool(makeLinks),allMakeRecordsHaveEarlierActualConstructor=all(x['constructor'] is not None for x in makeLinks),oneConfigurationPerCreatedCamera=len(configs)==len(constructors) and all(x['constructor'] is not None for x in configs) and sorted(x['constructor']['sequence'] for x in configs if x['constructor'])==sorted(x['sequence'] for x in constructors),allFitsHaveEarlierSameCameraConfiguration=all(x['configuration'] is not None for x in fits),everyActuallyMadePathHasFit=made<=fitted,actualCameraComponentsOrthographic=bool(cameraRows) and all(r['orthographicPresent'] is True and r['perspectivePresent'] is False for r in cameraRows),actualClipsUnchanged=all(math.isfinite(r['near']) and abs(r['near']-.1)<1e-6 and r['far']==100 for r in cameraRows),finitePositiveOrthographicScale=all(math.isfinite(r['orthographicScale']) and r['orthographicScale']>0 for r in cameraRows),fitGeometryInsideClips=all(x['fit']['allDepthsFinite'] and x['fit']['allDepthsInsideUnchangedClips'] and x['fit']['framingVertexCount']>0 for x in fits),noUnknownLifecycleOrCameraEvent=not unknown,completeTailAfterAllCaptures=len(caps)==12 and tail['epoch']>max(c['endEpoch'] for c in caps) and any(r==tail for r in rows))
report=dict(checks=checks,traceSHA256=hashlib.sha256(raw).hexdigest(),finalActualCounts=expected,constructorRecords=constructors,makeConstructorAssociations=makeLinks,cameraConfigurationAssociations=configs,fitAssociations=fits,allCameraRecords=cameraRows,unknownEvents=unknown,limitations=['No fixed historical constructor count imposed; every actual created kind and camera is reported.','Association uses source synchronous constructor/configuration order and current pointer record; IDs may be reused and do not establish concurrent lifetime.','Constructor/make/fit records are not proof the hand pixels appeared. Review each whole image separately for actual visibility and pose.','Uncreated single/pair path is not runtime covered; no gestures or new camera pose exercise is added.'])
out=p/'real-hand-lifetime-camera-validation.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(checks=checks,finalActualCounts=expected),indent=2));assert all(checks.values())
