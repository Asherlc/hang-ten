from pathlib import Path
import json,sys
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
def measured(name):
 p=base/name;h=json.loads((p/'hand-lifetime-validation.json').read_text());c=json.loads((p/'hand-camera-validation.json').read_text())
 return {'counts':h['finalCounts'],'boardFrames':sorted({tuple(v['frameInWindow']) for r in h['boardFrameHistory'] for v in r['boardHosts']}),'rootTransforms':sorted({tuple(r['rootTransform']) for r in h['boardFrameHistory'] if r['rootTransform']}),'boardCameraTransforms':sorted({tuple(r['cameraTransform']) for r in h['boardFrameHistory'] if r['cameraTransform']}),'handCameraTransforms':[r['cameraTransform'] for r in c['cameraRecords']],'handCameraDepths':[(r.get('minimumDepth'),r.get('maximumDepth'),r.get('framingVertexCount')) for r in c['cameraRecords']],'creationOrder':[(r['event'],r['detail'],r['kind']) for r in c['creationOrder']]}
a=measured('all-hand-projection-o1-landscape');b=measured(sys.argv[1]);checks={k:a[k]==b[k] for k in a};p=base/sys.argv[1]/'control-correspondence.json';assert not p.exists();p.write_text(json.dumps({'checks':checks,'orthographicControl':a,'thisArm':b,'scope':'Exact observed sets and sparse lifecycle order; not a claim of identical wallclock scheduling.'},indent=2)+'\n');print(json.dumps(checks,indent=2));assert all(checks.values())
