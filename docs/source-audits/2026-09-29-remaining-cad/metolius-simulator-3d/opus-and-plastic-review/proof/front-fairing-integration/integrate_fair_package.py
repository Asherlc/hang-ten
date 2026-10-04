import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review'
candidate = root / '.context/placid-badger/metolius-simulator-3d-front-fairing/candidate'
slug = 'metolius-simulator-3d'
package = root / 'Hangboards' / slug
batch = root / 'docs/source-audits/2026-09-29-remaining-cad'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
sys.path.insert(0, str(root / 'Tools/HangboardPackages/src'))
from hangboard_packages.cad_source import generate_board_json

assert len(sys.argv) == 4, 'Supply reviewed final source, model and descriptor hashes.'
names = [slug + '.FCStd', 'assets/primary.usdz', 'assets/primary.model.json']
expected = dict(zip(names, sys.argv[1:]))
prior = dict(zip(names, [
    '3ff3a89170bf35daa24a19f2f3e2226390d47359dcbcf9bdadcd1eed0330af6d',
    '78fd9fa2c09bea9905bcf47ccd71b77389c5e2999a5dace5994a2867f622ff6a',
    'e93ca8f6f13d2e30b3de7eadad91b0ba8bd05f6f282e21ce9b250304500115df',
]))
for name in names:
    assert sha(candidate / name) == expected[name], name
    assert sha(package / name) == prior[name], name
assert load(candidate / names[2])['modelSHA256'] == expected[names[1]]
manifest = generate_board_json(package / names[0])
assert generate_board_json(candidate / names[0]) == manifest
data = json.loads(manifest)
assert len(data['contacts']) == 30
assert data['presentations'][0]['media']['display']['surfaceFinish'] == 'plastic'
assert not (package / 'board.json').exists()
baseline = load(scratch / 'all-hangboards-baseline.json')
outside = {p: h for p, h in baseline.items() if not p.startswith('Hangboards/' + slug + '/')}
assert len(baseline) == 206 and len(outside) == 203
assert all(sha(root / p) == h for p, h in outside.items())
current = {str(p.relative_to(root)): sha(p) for p in (root / 'Hangboards').rglob('*') if p.is_file()}
assert set(current) == set(baseline)
save(scratch / 'pre-front-fairing-integration-package-hashes.json', current)

spec = importlib.util.spec_from_file_location('delivery', root / 'scripts/verify-model-delivery.py')
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
lock_path = root / 'docs/model-delivery-lock.json'
lock = load(lock_path)
assert delivery.verify(root, lock)['passed']
assert lock['sha256Manifest'] == 'ec620b346bf520d2f32f2069e02b07ad5d2f9fd6dc8c8ed6063b2d68f5ff38c7'
backup = scratch / 'before-front-fairing-integration'
backup.mkdir(exist_ok=True)
for path in [lock_path, batch / 'delivery-checksums.txt', batch / 'delivery-validation.json',
             batch / 'installed-delivery-validation.json', batch / 'batch-validation.json', batch / 'review-queue.json']:
    dest = backup / path.name
    assert not dest.exists(), 'Do not overwrite prior raw integration records.'
    shutil.copyfile(path, dest)
for name in names:
    dest = backup / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(package / name, dest)
    shutil.copyfile(candidate / name, package / name)
    assert sha(package / name) == expected[name]
assert generate_board_json(package / names[0]) == manifest
assert all(sha(root / p) == h for p, h in outside.items())

entry = lock['migratedPackages'][slug]
entry.update(sourceSHA256=expected[names[0]], assetSHA256=expected[names[1]],
             descriptorSHA256=expected[names[2]],
             geometryAcceptance='pending corrected plastic human review #8',
             nativeValidation='The lower front profile has a smooth monotonic taper, removing repeated full-width row bands while keeping native depth anchors. Center jug uses a forward rounded crest and rear return; flat/round sloper support bands reach the front with original 55/65 mm spans. All 30 contact facts, published face and 27 depth checks preserved. Plastic is the existing app display finish; rear clearance, forward anchors, rolls, thickness and blends are display adaptations requiring visual review.')
entry['assets']['assets/primary.usdz'].update(modelSHA256=entry['assetSHA256'],
                                            descriptorSHA256=entry['descriptorSHA256'])
checksums = delivery.checksum_manifest(root, lock['modelPackages'])
old_digest = lock['sha256Manifest']
digest = hashlib.sha256(checksums.encode()).hexdigest()
assert digest != old_digest
assert all(isinstance(x, str) for x in lock.get('sha256ManifestHistory', []))
lock.setdefault('sha256ManifestHistory', []).append(old_digest)
lock.update(supersededSha256Manifest=old_digest, sha256Manifest=digest)
save(lock_path, lock)
(batch / 'delivery-checksums.txt').write_text(checksums)
report = delivery.verify(root, lock)
assert report['passed'] and report['models'] == 58 and report['files'] == 135
save(scratch / 'delivery-validation.json', report)
save(batch / 'delivery-validation.json', report)
identity = {'owner': root.name, 'package': slug,
            'sourceSHA256': expected[names[0]], 'modelSHA256': expected[names[1]],
            'descriptorSHA256': expected[names[2]], 'surfaceFinish': 'plastic',
            'manifestBytesUnchangedFromPlasticIntermediate': True,
            'contactsUnchanged': 30, 'allOtherPackageFilesUnchanged': 203,
            'priorDeliveryDigest': old_digest, 'deliveryDigest': digest,
            'priorAssetCommit': 'ca5024c3b62f5ecc87e669e1ecab398e650b3890',
            'revisionBaseCommit': 'b097aa5ba34d55e69b9cdac73122b06774947a16',
            'humanGeometryAcceptance': 'pending smoothed-face corrected review #8', 'revision': 'forward-grasp-fair-face-and-plastic'}
save(scratch / 'front-fairing-integrated-package.json', identity)
save(scratch / 'integrated-package.json', identity)
print(json.dumps(identity, indent=2))
