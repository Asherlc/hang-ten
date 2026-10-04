from pathlib import Path
import json,sys
p=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')/sys.argv[1]
rows=[json.loads(l) for f in p.glob('events-*.jsonl') for l in f.read_text().splitlines()]
env=json.loads((p/'launch-review-environment.json').read_text());off=env.get('HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS')=='1';keys=['single.constructor-entry','single.make-entry','pair.constructor-entry','pair.make-entry']
counts=[r.get('handLifecycleCounts') for r in rows];tail=json.loads((p/'following-preview-tail.json').read_text())['record'];caps=json.loads((p/'captures.json').read_text());events=[r for r in rows if r['event']=='hand-lifecycle']
checks={'completeOpeningStream':rows[0]['event']=='recorder-open' and rows[0]['sequence']==1 and all(r['complete'] for r in rows) and [r['sequence'] for r in rows]==list(range(1,len(rows)+1)), 'instrumentationVersion':rows[0]['handLifecycleInstrumentationVersion']==1,'suppressionFlagCorrect':rows[0]['suppressesAllHandHosts']==off,'allFourCountsOnEveryRecord':all(c is not None and set(c)==set(keys) for c in counts),'openingCountsZero':counts[0]==dict.fromkeys(keys,0),'countsMonotonic':all(counts[i+1][k]>=counts[i][k] for i in range(len(counts)-1) for k in keys),'finalMarkerAfterLastCapture':tail['epoch']>max(c['endEpoch'] for c in caps) and any(r['sequence']==tail['sequence'] and r==tail for r in rows),'noRecorderErrorOrCap':len(rows)<4096 and not any(r['event'] in ['recorder-error','recorder-failure'] for r in rows)}
if off:checks['strictOFFZeroAllFourLifetimeCounts']=all(c==dict.fromkeys(keys,0) for c in counts) and not events
else:checks['ONUsedPathPositiveConstructorAndMake']=any(counts[-1][kind+'.constructor-entry']>0 and counts[-1][kind+'.make-entry']>0 for kind in ['single','pair'])
placements=[]
for r in rows:
 if 'applicationCensus' not in r or 'boardRenderMembership' not in r:continue
 scene=r['boardRenderMembership']['rootRealitySceneID']
 hosts=[v for s in r['applicationCensus']['windowScenes'] for w in s['windows'] for v in w.get('rendererPlacements',[]) if v.get('realitySceneID')==scene]
 placements.append({'sequence':r['sequence'],'epoch':r['epoch'],'event':r['event'],'boardHosts':hosts,'viewportPoints':r.get('viewportPoints'),'rootTransform':r.get('rootTransform'),'cameraTransform':r.get('cameraTransform')})
report={'checks':checks,'off':off,'finalCounts':counts[-1],'lifecycleEvents':events,'finalMarker':tail,'boardFrameHistory':placements,'limitations':['Counters cover the two app hand scene constructors and two RealityView make entries through retained final marker; not all framework GPU activity or future lifetime.','No compensating layout applied; actual frame history retained.']};f=p/'hand-lifetime-validation.json';assert not f.exists();f.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'checks':checks,'finalCounts':counts[-1]},indent=2));assert all(checks.values())
