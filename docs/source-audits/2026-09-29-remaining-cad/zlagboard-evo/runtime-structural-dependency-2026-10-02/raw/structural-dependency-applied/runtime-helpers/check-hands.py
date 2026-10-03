from pathlib import Path
import json,sys
p=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')/sys.argv[1]
rows=[json.loads(l) for f in p.glob('events-*.jsonl') for l in f.read_text().splitlines()];env=json.loads((p/'launch-review-environment.json').read_text());camera=[r for r in rows if r['event']=='hand-camera'];life=[r for r in rows if r['event']=='hand-lifecycle'];counts=[r['handLifecycleCounts'] for r in rows]
checks=dict(strictFlagEnabled=env.get('HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS')=='1',perspectiveFlagAbsent='HANGTEN_REVIEW_ALL_HAND_PERSPECTIVE' not in env,openingStrictEnabled=rows[0]['suppressesAllHandHosts'],allFourCountsZeroThroughout=all(all(v==0 for v in x.values()) and len(x)==4 for x in counts),noHandLifecycleEvents=not life,noHandCameraEvents=not camera)
out=p/'strict-absence-validation.json';assert not out.exists();out.write_text(json.dumps(dict(checks=checks,recordCount=len(rows),cameraEvents=camera,lifecycleEvents=life,scope='Complete retained recorder-open through finaltail; no future-lifetime claim.'),indent=2)+'\n');print(json.dumps(checks,indent=2));assert all(checks.values())
