"""Prepare scoped review records only after the corrected packet is installed."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

parser = argparse.ArgumentParser()
parser.add_argument('--config', type=Path, required=True)
args = parser.parse_args()
ROOT = Path.cwd()
BASE = ROOT / '.context/placid-badger/nature-stone-review9'
LANE = BASE / 'vertical-groove-correction'
IOS = BASE / 'vertical-groove-ios'
AUDIT = 'docs/source-audits/2026-09-29-remaining-cad'
PACKET = AUDIT + '/nature-stone-hanger/display-and-pose-review'
QUEUE_PACKET = 'nature-stone-hanger/display-and-pose-review'
OUT = LANE / 'record-update.json'
assert not OUT.exists(), 'Retain earlier preparation'
config = json.loads(args.config.read_text())
assert config['finalReady'] is True
identity = config['identity']
visual = json.loads((LANE / 'root-final-visual-review.json').read_text())
assert visual['status'] == 'pass' and not visual['blockingFindings']
assert visual['allEightContactsReviewed'] and visual['wholeImagesViewed'] >= 17
assert visual['sameInstanceGraniteRestorationReviewed']
for name in ('sourceSHA256', 'modelSHA256', 'descriptorSHA256', 'sidecarSHA256'):
    assert visual[name] == identity[name]
ios = json.loads((IOS / 'final-runtime-review.json').read_text())
assert ios['status'] == 'passed' and not ios['blockingFindings']
assert ios['tests']['failed'] == ios['tests']['skipped'] == 0
assert ios['tests']['passed'] > 0
assert set(ios['tests']['classes']) == {
    'BoardModelTests', 'BoardModelRealityTests', 'BoardPackageStoreTests',
    'SuspendedBoardPresentationTests'}
python = json.loads((LANE / 'package-checks/final-python-tests.json').read_text())
assert python['status'] == 'pass' and python['passed'] > 0
assert python['failed'] == python['skipped'] == 0
assert python['packageBytesStable'] and python['ownedTemporaryDirectoryAbsent']
installed = json.loads((IOS / 'installed-app-provenance.json').read_text())
assert installed['binaryBytesMatch'] and installed['generatedManifestBytesMatchSource']
assert installed['builtBinarySHA256'] == ios['builtInstalledBinarySHA256'] == visual['builtBinarySHA256']
assert installed['generatedManifestSHA256'] == ios['generatedManifestSHA256']
assert installed['packageSHA256'] == ios['packageSHA256'] == python['packageSHA256']
proposal = json.loads((ROOT / PACKET / 'human-review-proposal.json').read_text())
assert proposal['status'] == 'pending' and proposal['identity'] == identity
old_lock = json.loads((BASE / 'before-global-records/model-delivery-lock.json').read_text())
date = datetime.now(timezone.utc).date().isoformat()
tests = {'pythonPassed': python['passed'], 'pythonSkipped': 0,
         'iOSPassed': ios['tests']['passed'], 'iOSSkipped': 0, 'failures': 0}
native_images = [p.name for p in (ROOT / PACKET).glob('native-*.png')]
assert native_images, 'The changed geometry must have whole native comparisons'
revision = {
    'package': 'nature-stone-hanger', 'date': date,
    'revision': 'vertical-cord-seats-granite-short-cord-and-weightable-poses',
    'feedback': config['humanFeedback'], 'sourceSHA256': identity['sourceSHA256'],
    'modelSHA256': identity['modelSHA256'], 'descriptorSHA256': identity['descriptorSHA256'],
    'suspensionSHA256': identity['sidecarSHA256'],
    'report': PACKET + '/runtime-validation.json', 'postIntegrationTests': tests,
    'allOtherPackageFilesUnchanged': 202, 'boardFactsAndContactIDsUnchanged': True,
    'nativeBodyGeometryChanged': True, 'surfaceFinish': 'wood',
    'graniteNodeIDs': ['edge_front_20mm_granite_mesh_001'], 'positions': 8,
    'certifiedCordBranches': 16, 'verticalGrooves': 2, 'transverseNotchesPreserved': 6,
    'geometryAcceptance': 'pending one-by-one user review',
    'humanReviewRecord': AUDIT + '/nature-stone-hanger/human-review.json',
    'limits': ' '.join(config['limits']),
    'priorDeliveryManifestSHA256': old_lock['sha256Manifest']}
asset = {'modelSHA256': identity['modelSHA256'], 'descriptorPath': 'assets/primary.model.json',
         'descriptorSHA256': identity['descriptorSHA256']}
frames = visual['wholeImagesViewed']
drags = visual['actualDragChecks']
assert isinstance(drags, int)
assert drags >= 5
update = {
    'rootFinalReviewConfirmed': True, 'identity': identity, 'revision': revision,
    'lockEntry': {
        'sourceSHA256': identity['sourceSHA256'], 'suspensionSHA256': identity['sidecarSHA256'],
        'assetSHA256': identity['modelSHA256'], 'descriptorSHA256': identity['descriptorSHA256'],
        'assets': {'assets/primary.usdz': asset},
        'geometryAcceptance': 'pending one-by-one user review',
        'comparison': PACKET + '/index.html', 'nativeAppValidation': PACKET + '/runtime-validation.json',
        'latestRevision': PACKET + '/review.md',
        'nativeValidation': 'Added one longitudinal cord seat per side; preserved all six transverse adjustment notches, eight native contact surfaces and factual metadata. Fresh native, unbound export, all-pose cord seating/entry/clearance, independently checked material-facet reactions and regenerated cache proofs are retained with exact asset hashes in the review packet.'},
    'queueEntry': {
        'sourceSHA256': identity['sourceSHA256'], 'suspensionSHA256': identity['sidecarSHA256'],
        'humanReview': 'pending', 'reviewPage': QUEUE_PACKET + '/index.html',
        'presentations': {'primary': {'modelSHA256': identity['modelSHA256'],
                                     'descriptorSHA256': identity['descriptorSHA256']}},
        'comparisons': [QUEUE_PACKET + '/' + p['output'] for p in config['appPairs']]
                       + [QUEUE_PACKET + '/' + n for n in sorted(native_images)],
        'appReview': QUEUE_PACKET + '/runtime-validation.json', 'appReviewPage': QUEUE_PACKET + '/index.html',
        'humanReviewRecord': 'nature-stone-hanger/human-review.json',
        'reviewFeedback': config['humanFeedback'], 'routingClarification': config['routingClarification'],
        'latestRevision': QUEUE_PACKET + '/review.md', 'runtimeRevision': QUEUE_PACKET + '/runtime-validation.json'},
    'batchReport': PACKET + '/runtime-validation.json',
    'installedDeliveryUpdate': {
        'date': date, 'scope': 'Corrected Nature Stone Hanger installed package only; prior all-catalog delivery record is retained as historical evidence.',
        'sourceSHA256': identity['sourceSHA256'], 'suspensionSHA256': identity['sidecarSHA256'],
        'modelSHA256': identity['modelSHA256'], 'descriptorSHA256': identity['descriptorSHA256'],
        'builtInstalledBinarySHA256': ios['builtInstalledBinarySHA256'],
        'generatedManifestSHA256': ios['generatedManifestSHA256'],
        'binaryBytesMatch': True, 'generatedManifestBytesMatchSource': True,
        'exactContactSelections': 8, 'wholeFramesReviewed': frames, 'actualDrags': drags,
        'sameInstanceGraniteRestoration': True, 'postIntegrationTests': tests,
        'cleanupVerified': True, 'report': PACKET + '/runtime-validation.json', 'humanAcceptance': 'pending'},
    'humanReviewRecord': {
        'reviewPacket': PACKET + '/index.html', 'runtimeValidation': PACKET + '/runtime-validation.json',
        'datePrepared': date, 'technicalGates': 'pass', 'status': 'pending',
        'postIntegrationTests': tests, 'reviewedFrames': frames, 'reviewedContacts': 8}}
OUT.write_text(json.dumps(update, indent=2) + '\n')
print(json.dumps({'path': str(OUT.relative_to(ROOT)),
                  'sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(), 'humanAcceptance': 'pending'}))
