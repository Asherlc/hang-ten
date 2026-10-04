"""Update #9 identities after fresh runtime review, preserving all historical rows."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import importlib.util
import json

ROOT = Path.cwd()
BASE = ROOT / '.context/placid-badger/nature-stone-review9/granite-seat-correction'
AUDIT = ROOT / 'docs/source-audits/2026-09-29-remaining-cad'
PACKET = AUDIT / 'nature-stone-hanger/granite-seat-review'
PREFIX = str(PACKET.relative_to(ROOT))
SHORT = 'nature-stone-hanger/granite-seat-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

inputs = read(BASE / 'ios/final-inputs.json')
assert inputs['rootFinalHashReady']
assert {p: sha(ROOT / p) for p in inputs['packageSHA256']} == inputs['packageSHA256']
runtime = read(PACKET / 'runtime-validation.json')
assert runtime['status'] == 'pass'
assert runtime['packageSHA256'] == inputs['packageSHA256']
assert runtime['resourceCleanupVerified'] is True
assert runtime['wholeFramesReviewed'] == 25
assert runtime['contactsReviewed'] == 8 and runtime['actualDrags'] == 9
tests = runtime['postIntegrationTests']
assert tests['pythonPassed'] == 260 and tests['pythonSkipped'] == 0
assert tests['iOSPassed'] > 0 and tests['iOSSkipped'] == 0 and tests['failures'] == 0
others = read(BASE / 'other-package-baseline.json')
assert {p: sha(ROOT / p) for p in others} == others
source = inputs['packageSHA256']['Hangboards/nature-stone-hanger/nature-stone-hanger.FCStd']
model = inputs['packageSHA256']['Hangboards/nature-stone-hanger/assets/primary.usdz']
desc = inputs['packageSHA256']['Hangboards/nature-stone-hanger/assets/primary.model.json']
sidecar = inputs['packageSHA256']['Hangboards/nature-stone-hanger/suspension.json']
feedback = 'The granite is overlapping with wood, look at photos'
date = datetime.now(timezone.utc).date().isoformat()
revision = {
    'package': 'nature-stone-hanger', 'date': date,
    'revision': 'granite-insert-fitted-into-wood-seat', 'feedback': [feedback],
    'sourceSHA256': source, 'modelSHA256': model,
    'descriptorSHA256': desc, 'suspensionSHA256': sidecar,
    'report': PREFIX + '/runtime-validation.json',
    'postIntegrationTests': tests,
    'boardFactsAndContactIDsUnchanged': True,
    'otherPackageFilesUnchanged': len(others),
    'nativeWoodStoneOverlapMM3': 0,
    'exportedGraniteWoodPlanarOverlapMM2': 0,
    'otherSevenNativeContactSurfacesUnchanged': True,
    'graniteContactDepthMM': 20,
    'surfaceFinish': 'wood',
    'graniteNodeIDs': ['edge_front_20mm_granite_mesh_001'],
    'positions': 8, 'recertifiedCordBranches': 16,
    'cordRoutesAndTranslationsPreserved': True,
    'onlySidecarChangedFields': ['modelSHA256', 'ropeSolver/grooveGuides/sourceSHA256'],
    'geometryAcceptance': 'pending one-by-one user review',
    'humanReviewRecord': str((AUDIT / 'nature-stone-hanger/human-review.json').relative_to(ROOT)),
    'limits': 'Primary photos establish a seated insert and lower opening shape. Precise insert dimensions, local rounds, pocket shape and runtime texture remain display estimates. The existing solver-generated routes were freshly re-certified against the corrected native solid; they were not regenerated. No hidden construction or real load safety claim. Twenty-five whole app frames and nine drags cover representative views, not every continuous camera angle. Prior revision proofs remain historical and are not carried forward or added to fresh test counts.',
}

lock_path = ROOT / 'docs/model-delivery-lock.json'
lock = read(lock_path)
prior_lock = read(BASE / 'prior-records/model-delivery-lock.json')
row = lock['migratedPackages']['nature-stone-hanger']
row.update(sourceSHA256=source, assetSHA256=model, descriptorSHA256=desc,
           suspensionSHA256=sidecar, comparison=PREFIX + '/index.html',
           latestRevision=PREFIX + '/review.md',
           nativeAppValidation=PREFIX + '/runtime-validation.json',
           geometryAcceptance='pending one-by-one user review',
           nativeValidation='Fitted native wood seat and exposed granite-only contact. Native interpenetration and exported material overlap are zero. All eight contact depths checked; seven other native surfaces and factual metadata preserved. Existing routes re-certified against the updated native solid for all eight poses and 16 branches; no new route authoring. Fresh exact-asset export and app proofs retained in granite-seat-review.')
row['assets']['assets/primary.usdz'].update(modelSHA256=model, descriptorSHA256=desc)
spec = importlib.util.spec_from_file_location('verify_model_delivery', ROOT / 'scripts/verify-model-delivery.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
manifest = verify.checksum_manifest(ROOT, lock['modelPackages'])
old_text = (AUDIT / 'delivery-checksums.txt').read_text()
before_rows = {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in old_text.splitlines()}
after_rows = {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in manifest.splitlines()}
assert set(before_rows) == set(after_rows)
changed = {path for path in before_rows if before_rows[path] != after_rows[path]}
assert changed == {p for p in inputs['packageSHA256'] if not p.endswith('.usdz')}
(PACKET / 'prior-delivery-checksums.txt').write_text(old_text)
digest = hashlib.sha256(manifest.encode()).hexdigest()
lock.setdefault('sha256ManifestHistory', []).append({
    'sha256Manifest': lock['sha256Manifest'], 'date': date,
    'reason': 'Nature Stone Hanger fitted granite seat; prior manifest preserved',
    'path': PREFIX + '/prior-delivery-checksums.txt'})
revision['priorDeliveryManifestSHA256'] = lock['sha256Manifest']
lock['sha256Manifest'] = digest
lock.setdefault('individualReviewRevisions', []).append(copy.deepcopy(revision))
for name in lock['migratedPackages']:
    if name != 'nature-stone-hanger':
        assert lock['migratedPackages'][name] == prior_lock['migratedPackages'][name]
write(lock_path, lock)
(AUDIT / 'delivery-checksums.txt').write_text(manifest)
delivery = verify.verify(ROOT, lock)
assert delivery['passed'] and delivery['models'] == 58 and delivery['files'] == 135
write(AUDIT / 'delivery-validation.json', delivery)

queue_path = AUDIT / 'review-queue.json'
queue = read(queue_path)
prior_queue = read(BASE / 'prior-records/review-queue.json')
board = queue['boards'][8]
assert board['package'] == 'nature-stone-hanger' and board['humanReview'] == 'pending'
board.update(sourceSHA256=source, suspensionSHA256=sidecar,
             reviewPage=SHORT + '/index.html', appReviewPage=SHORT + '/index.html',
             appReview=SHORT + '/runtime-validation.json',
             latestRevision=SHORT + '/review.md', runtimeRevision=SHORT + '/runtime-validation.json',
             comparisons=[SHORT + '/native-front-side-top.png'] +
             [SHORT + '/export-' + v + '.png' for v in ['front', 'side', 'top', 'oblique']])
board['presentations']['primary'].update(modelSHA256=model, descriptorSHA256=desc)
board['reviewFeedback'].append(feedback)
for i, other in enumerate(queue['boards']):
    if i != 8:
        assert other == prior_queue['boards'][i]
write(queue_path, queue)

batch_path = AUDIT / 'batch-validation.json'
batch = read(batch_path)
batch.setdefault('reviewRevisions', []).append(copy.deepcopy(revision))
write(batch_path, batch)
installed_path = AUDIT / 'installed-delivery-validation.json'
installed = read(installed_path)
assert 'stoneHangerGraniteSeatReview9' not in installed
installed['stoneHangerGraniteSeatReview9'] = dict(
    date=date, scope='Fresh installed Nature Stone Hanger granite-seat revision only; prior catalog and Stone Hanger records remain historical.',
    sourceSHA256=source, modelSHA256=model, descriptorSHA256=desc, suspensionSHA256=sidecar,
    installedParity=runtime['installedParity'], exactContactSelections=8,
    wholeFramesReviewed=25, actualDrags=9, sameInstanceGraniteRestoration=True,
    postIntegrationTests=tests, cleanupVerified=True,
    report=PREFIX + '/runtime-validation.json', humanAcceptance='pending')
write(installed_path, installed)

human_path = AUDIT / 'nature-stone-hanger/human-review.json'
human = read(human_path)
human.setdefault('priorRevisions', []).append({
    key: copy.deepcopy(value) for key, value in human.items() if key != 'priorRevisions'})
human['feedback'].append(feedback)
human['identity'].update(sourceSHA256=source, modelSHA256=model,
                         descriptorSHA256=desc, sidecarSHA256=sidecar)
human.update(reviewScope='Fitted granite insert and wood opening; whole prior/current native and export comparisons; fresh app seams upright/inverted from front and both sides; all eight selections, nine drags and same-instance finish restoration.',
             reviewPacket=PREFIX + '/index.html', runtimeValidation=PREFIX + '/runtime-validation.json',
             datePrepared=date, technicalGates='pass', postIntegrationTests=tests,
             reviewedFrames=25, reviewedContacts=8, status='pending',
             globalRecordsUpdatedByThisBuilder=True)
write(human_path, human)
write(PACKET / 'delivery-record-update.json', {
    'status': 'pass', 'packageSHA256': inputs['packageSHA256'],
    'changedChecksumRows': sorted(changed), 'deliveryManifestSHA256': digest,
    'allOtherPackageFilesUnchanged': len(others),
    'allOtherReviewQueueRowsUnchanged': True,
    'humanAcceptance': 'pending'})
print(json.dumps({'status': 'pass', 'deliveryManifestSHA256': digest,
                  'changedChecksumRows': sorted(changed), 'humanReview': 'pending'}))
