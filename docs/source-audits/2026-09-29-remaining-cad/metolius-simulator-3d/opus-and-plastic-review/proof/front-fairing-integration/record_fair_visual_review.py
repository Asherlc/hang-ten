from pathlib import Path
import hashlib
import json
import sys

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review'
fair = root / '.context/placid-badger/metolius-simulator-3d-front-fairing'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
identity = load(scratch / 'integrated-package.json')
assert identity['sourceSHA256'] == 'b7223032abe4b5c00a8b16d8ddcafed8b836d806795f1d37bbffab80ce5560ef'
assert len(sys.argv) == 2 and sys.argv[1] in ('geometry', 'app')
names = ('sourceSHA256', 'modelSHA256', 'descriptorSHA256')
bound = {k: identity[k] for k in names}
paths = []

if sys.argv[1] == 'geometry':
    for folder in ('review', 'export-review'):
        paths.extend(fair / folder / ('comparison-' + name + '.png')
                     for name in ('front', 'side', 'top', 'oblique', 'raking'))
    paths.append(fair / 'native-profile-sections.png')
    paths.extend(fair / 'grasp-review' / (name + '.png')
                 for name in ('high-front', 'rear-center', 'rear-oblique', 'native-grasp-sections'))
    paths.extend(fair / 'export-grasp-review' / ('candidate-' + name + '.png')
                 for name in ('high-front', 'rear-center', 'rear-oblique', 'grasp-sections'))
    assert len(paths) == 19 and all(p.is_file() for p in paths)
    reports = [fair / 'author-report.json', fair / 'reproducibility.json',
               fair / 'independent-validation/final-independent-native-review-b722-labels-v2.json',
               fair / 'independent-validation/final-independent-export-review-b722.json',
               fair / 'independent-validation/actual-owner-normal-supplement-b722.json',
               fair / 'independent-validation/export-rear-correspondence-b722-v2.json',
               scratch / 'opus-fairing-native-review.md', scratch / 'opus-fairing-native-activity.json']
    assert load(reports[3])['status'] == 'pass'
    assert all(load(reports[3])[k] == bound[k] for k in names)
    report = {'owner': root.name, 'status': 'pass', 'blockingFindings': [], **bound,
              'scope': 'Root inspected 19 complete native and exact-export images. Technical geometry disposition; actual app appearance and human acceptance are separate.',
              'changesVerified': ['Repeated full-width lower-face bands removed with a smooth monotonic taper through retained native depth anchors',
                                  'Protected upper grip region unchanged, with a forward center-jug crest and rear return',
                                  'Flat and round sloper roofs and 55/65 mm contact bands reach the front',
                                  'Dome face shelf remains removed, flat front edge remains rounded, and X47 contact boundary remains intact'],
              'factsPreserved': {'contacts': 30, 'depthChecks': 27, 'faceMM': [711, 222]},
              'allImagesInspectedWhole': True, 'pixelDerivedGeometry': False,
              'strictToleranceChange': False,
              'normalOracleDisposition': 'Original legacy comparison remains review-required. Independent supplemental pass uses the exact unique native face owner for its one disputed corner; no compiler, source or tolerance change.',
              'rearDisposition': 'Perspective CPU mark is visible. All 583 native rear triangles correspond exactly after float32 encoding and all rear normals and winding face the wall. Actual app appearance remains a required check.',
              'actualAppWatchItems': ['Remaining single upper roll transition', 'Outer saddle and flat sloper front edge',
                                     'Center jug cap and upper pocket lip', 'Rear flat face and center hump',
                                     'Contact highlights and mint restoration'],
              'limits': ['Lower taper, rear return, forward anchoring, rounding, thickness and blends are display adaptations.',
                         'Native solid is closed. Semantic export has 2974 boundary edges and 62 nonmanifold edges, with localized opposing-normal slivers of 6.849906 mm2; exact welded closure and universal corner-normal alignment are not claimed.',
                         'Finite mesh coverage passes 0.28 mm and published facts pass 0.001 mm; neither is manufacturer certification.',
                         'Mint is the app palette; USDZ is unbound.'],
              'humanAcceptance': 'pending revised #8'}
    destination = scratch / 'geometry-disposition.json'
else:
    phases = ('after', 'finish-checks', 'grasp-checks')
    records = [load(scratch / 'ios' / (phase + '-captures') / 'validation.json') for phase in phases]
    assert [len(r['checks']) for r in records] == [8, 4, 4]
    assert all(all(r[k] == bound[k] for k in names) for r in records)
    assert all(r['surfaceFinish'] == 'plastic' for r in records)
    binary = load(scratch / 'ios/installed-app-provenance.json')['installedBinarySHA256']
    assert all(r['builtBinarySHA256'] == binary for r in records)
    assert [sum(bool(c.get('actualDragOrbit')) for c in r['checks']) for r in records] == [3, 1, 3]
    assert len(records[2]['actualDragChecks']) == 6
    for phase, r in zip(phases, records):
        for c in r['checks']:
            paths.append(scratch / 'ios' / (phase + '-captures') / c['image'])
    assert len(paths) == 16 and all(p.is_file() for p in paths)
    reports = [scratch / 'ios' / (phase + '-captures') / 'validation.json' for phase in phases]
    reports += [scratch / 'ios/installed-app-provenance.json', scratch / 'geometry-disposition.json']
    report = {'owner': root.name, 'status': 'pass', 'blockingFindings': [], **bound,
              'builtBinarySHA256': binary, 'surfaceFinish': 'plastic',
              'scope': 'Root inspected all 16 complete new actual-app frames with source and installed binary provenance, representative selection and actual drag checks. Human acceptance of #8 remains pending.',
              'allImagesInspectedWhole': True, 'pixelDerivedGeometry': False,
              'checks': {'smoothLowerFaceWithoutRepeatedBands': True,
                         'singleUpperTransitionReadsAsUndersideOfRolledRoof': True,
                         'centerJugForwardCrestAndSmoothRearReturn': True,
                         'flatAndRoundSlopersReachFront': True,
                         'noCrossDomeShelfOrKnifeLikeUpperPocketLip': True,
                         'rearFlatFaceNoVisibleTriangleOrStreak': True,
                         'mintAcrossBoardAndVisibleRedSelection': True,
                         'sameInstanceSelectionRestoresMint': True,
                         'representativeAXSelectionAndActualOrbits': True},
              'actualOrbitFrames': 7, 'actualDragOperations': 10,
              'contactCount': 30, 'humanAcceptance': 'pending revised #8',
              'limits': ['Small teeth remain along selected top contact boundaries; board surfaces themselves are smooth in these app views.',
                         'Inherited outer-jug faceting and absent mouth bevels remain visible at some angles.',
                         'Rear return, lower taper, profile thickness and roll sizes are display adaptations; mint is the app palette.',
                         'Representative views and AX contact inventory do not constitute a visual sweep of every contact or manufacturer certification.']}
    destination = scratch / 'app-visual-review.json'

report['fileSHA256'] = {str(p.relative_to(root)): sha(p) for p in paths + reports}
save(destination, report)
print(json.dumps({'report': str(destination.relative_to(root)), 'status': report['status'],
                  'images': len(paths), 'SHA256': sha(destination), **bound}, indent=2))
