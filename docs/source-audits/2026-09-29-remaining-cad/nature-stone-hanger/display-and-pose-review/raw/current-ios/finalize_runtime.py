"""Publish the fresh focused runtime proof after physical review and cleanup."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT = Path.cwd()
LANE = ROOT / '.context/placid-badger/nature-stone-review9/vertical-groove-ios'
VISUAL = LANE.parent / 'vertical-groove-correction/root-final-visual-review.json'
OUT = LANE / 'final-runtime-review.json'
assert not OUT.exists(), 'Retain earlier runtime proof'
load = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = load(LANE / 'final-inputs.json')
assert inputs['rootFinalHashReady'] is True
assert all(sha(ROOT / p) == v for p, v in inputs['packageSHA256'].items())
installed = load(LANE / 'installed-app-provenance.json')
capture = load(LANE / 'final-captures/validation.json')
visual = load(VISUAL)
assert visual['status'] == 'pass' and not visual['blockingFindings']
assert visual['allEightContactsReviewed'] and visual['sameInstanceGraniteRestorationReviewed']
assert installed['packageSHA256'] == inputs['packageSHA256']
assert installed['binaryBytesMatch'] and installed['generatedManifestBytesMatchSource']
assert installed['builtBinarySHA256'] == capture['builtBinarySHA256'] == visual['builtBinarySHA256']
for name in ('sourceSHA256', 'modelSHA256', 'descriptorSHA256', 'sidecarSHA256'):
    assert capture[name] == visual[name]
assert {c['contactID'] for c in capture['checks']} == set(installed['contactIDs'])
assert len(installed['contactIDs']) == 8
assert len(capture['actualDragChecks']) == visual['actualDragChecks'] >= 5
assert all(c['selectionAXConfirmed'] and c['projectedContactFramesChanged']
           for c in capture['actualDragChecks'])
images = [p for p in (LANE / 'final-captures').glob('*.png')]
assert len(images) == visual['wholeImagesViewed'] >= 17
assert all(sha(LANE / 'final-captures' / n) == v for n, v in capture['fileSHA256'].items())
summary = load(LANE / 'ios-summary.json')
assert summary['failedTests'] == summary['skippedTests'] == 0
assert summary['passedTests'] > 0
commands = {kind: load(LANE / ('ios-' + kind + '-command.json')) for kind in ('build', 'tests')}
for record in commands.values():
    assert record['exitCode'] == 0 and record['cleanupVerified'] and record['ownedProcessGroupAbsent']
    try:
        os.killpg(record['ownedProcessGroup'], 0)
    except ProcessLookupError:
        pass
    else:
        raise AssertionError('Owned Xcode process group remains')
cleanup = load(LANE / 'ios-cleanup.json')
assert cleanup['cleanupStatus'] == 0
assert cleanup['derivedDataRemoved'] and cleanup['xcresultRemoved'] and cleanup['ownedTmpRemoved']
uid = load(LANE / 'ownership.json')['simulatorUUID']
assert uid == cleanup['simulator'] == installed['simulator'] == capture['simulator']
devices = json.loads(subprocess.check_output(
    ['rtk', 'proxy', 'xcrun', 'simctl', 'list', 'devices', '--json'], timeout=30))
assert not any(d['udid'] == uid for group in devices['devices'].values() for d in group)
for name in ('paseo-owned-simulators', 'paseo-pending-simulators'):
    p = ROOT / '.context' / name
    assert not p.exists() or uid not in p.read_text().splitlines()
assert not (ROOT / '.context/DerivedData').exists()
assert not (LANE / 'tmp').exists()
assert not (LANE / 'placid-badger-stone-vertical-groove-tests.xcresult').exists()
proof = {
    'status': 'passed', 'phase': 'vertical-groove-current-source',
    'humanAcceptance': 'pending review #9', 'blockingFindings': [],
    'packageSHA256': inputs['packageSHA256'],
    **{name: capture[name] for name in ('sourceSHA256', 'modelSHA256', 'descriptorSHA256', 'sidecarSHA256')},
    'builtInstalledBinarySHA256': installed['builtBinarySHA256'],
    'generatedManifestSHA256': installed['generatedManifestSHA256'],
    'commit': installed['commit'], 'dirtyDiffSHA256': installed['dirtyDiffSHA256'],
    'build': {k: commands['build'][k] for k in ('exitCode', 'elapsedSeconds')},
    'tests': {'passed': summary['passedTests'], 'failed': 0, 'skipped': 0,
              'classes': ['BoardModelTests', 'BoardModelRealityTests',
                          'BoardPackageStoreTests', 'SuspendedBoardPresentationTests'],
              'rawSummary': 'ios-summary.json'},
    'coverage': {'exactContactSelections': 8,
                 'wholeFrameScreenshotsPhysicallyInspected': len(images),
                 'actualDragActions': len(capture['actualDragChecks']),
                 'frontAndReverseSideOrbits': True,
                 'sameInstanceGraniteToWoodRestoration': True,
                 'relaunchReappearance': True,
                 'packageInstallParity': 'Nature Stone Hanger binary, generated manifest, descriptor and embedded ODR model exact'},
    'visualFindings': visual['findings'],
    'limits': ['Focused board runtime validation; human product acceptance remains pending.',
               'No workout, HealthKit, audio or landscape validation in this lane.',
               'Clear, reset and cord picking are covered by the focused runtime tests; relaunch captures alone do not prove same-instance clear/reset.',
               'Other installed packages and Android runtime are outside this parity check.'],
    'cleanup': {'status': 'passed', 'simulatorUUID': uid, 'actualUUIDAbsent': True,
                'derivedDataAbsent': True, 'ownedTmpAbsent': True, 'xcresultAbsent': True,
                'pendingAndOwnedRecordsConsumed': True,
                'ownedBuildAndTestProcessGroupsVerifiedAbsent': True},
    'fileSHA256': {str(p.relative_to(ROOT)): sha(p)
                   for p in sorted(LANE.rglob('*')) if p.is_file()}
}
proof['fileSHA256'][str(VISUAL.relative_to(ROOT))] = sha(VISUAL)
OUT.write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps({'status': proof['status'], 'tests': proof['tests'],
                  'frames': len(images), 'sha256': sha(OUT), 'humanAcceptance': 'pending'}))
