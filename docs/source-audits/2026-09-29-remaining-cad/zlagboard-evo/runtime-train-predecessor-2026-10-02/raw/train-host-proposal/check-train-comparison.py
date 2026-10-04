from pathlib import Path
import json,sys
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
a,b=[base/x for x in sys.argv[1:3]]
def details(p):
 host=json.loads((p/'normal-host-frame-validation.json').read_text());token=host['workoutSceneLifecycleToken'];rows=[json.loads(l) for f in p.glob('events-*.jsonl') for l in f.read_text().splitlines()]
 selected=[r for r in rows if r.get('sceneLifecycleToken')==token]
 return dict(endpoints=host['normalOwnEndpoints'],surfaceInputs=sorted({json.dumps(r['resolvedSurfaceInputs'],sort_keys=True) for r in selected if 'resolvedSurfaceInputs' in r}),rootTransforms=sorted({json.dumps(r['rootTransform']) for r in selected if 'rootTransform' in r}),cameraTransforms=sorted({json.dumps(r['cameraTransform']) for r in selected if 'cameraTransform' in r}),cameraProjection=sorted({json.dumps({k:r['boardRenderMembership'][k] for k in ['near','far','orthographic','perspective','verticalFOVDegrees']},sort_keys=True) for r in selected if 'boardRenderMembership' in r}),ownFrameChecks=host['checks'])
x,y=details(a),details(b);checks={k:x[k]==y[k] for k in ['endpoints','surfaceInputs','rootTransforms','cameraTransforms','cameraProjection']}
result=dict(checks=checks,arms={a.name:x,b.name:y},limitation='Actual workout metadata correspondence only. Clear Train placeholder slot unmeasured; its layout preservation is source-derived. Train subtree removal is the intervention bundle. Intermediate animation sample times need not coincide; each run retains its own monotone endpoint-path validation. No constructor-count inference of overlapping lifetime.')
out=b/'train-comparison.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2));assert all(checks.values())
