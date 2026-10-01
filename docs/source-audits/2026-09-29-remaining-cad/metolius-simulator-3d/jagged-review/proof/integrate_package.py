import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-jagged'
candidate = scratch / 'native-author/candidate'
before = scratch / 'native-author/before'
slug = 'metolius-simulator-3d'
package = root / 'Hangboards' / slug
batch = root / 'docs/source-audits/2026-09-29-remaining-cad'
audit = batch / slug
packet = audit / 'jagged-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
sys.path.insert(0, str(root / 'Tools/HangboardPackages/src'))
from hangboard_packages.cad_source import generate_board_json

assert len(sys.argv) == 4, 'Supply reviewed source, USDZ and descriptor SHA-256.'
names = [slug + '.FCStd', 'assets/primary.usdz', 'assets/primary.model.json']
expected = dict(zip(names, sys.argv[1:]))
original = dict(zip(names, [
    '9449f932e98c23fc9115d7a2cd0cfe5aacb158fd574d7ba573287ef7c5b67222',
    'a1d2a2a5e0cc4cc955ecf9b25c47b049bd71d8c70b3b2269fa167b9defbe6d16',
    '1c485ce852b600cb69eb1bf4036f73245b03cb88715e46f8ee789f3601f5115e',
]))
for name in names:
    assert sha(candidate / name) == expected[name], name
    assert sha(package / name) == sha(before / name) == original[name], name
assert load(candidate / names[2])['modelSHA256'] == expected[names[1]]
manifest = generate_board_json(before / names[0])
assert manifest == generate_board_json(candidate / names[0])
assert len(json.loads(manifest)['contacts']) == 30
assert not (package / 'board.json').exists()
baseline = {name: row['sha256'] for name, row in load(
    scratch / 'independent-validation/all-hangboards-baseline.json')['files'].items()}
current = {str(p.relative_to(root)): sha(p) for p in sorted((root / 'Hangboards').rglob('*')) if p.is_file()}
assert current == baseline, 'Package tree changed since independent baseline.'
assert len(current) == 206
save(scratch / 'pre-integration-package-hashes.json', current)

packet.mkdir(parents=True, exist_ok=True)
for name in names:
    target = packet / 'before' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(before / name, target)
    assert sha(target) == original[name]
(packet / 'before/generated-board.json').write_bytes(manifest)
for name in ['source-audit.md', 'human-review.json']:
    shutil.copyfile(audit / name, packet / 'before' / name)
for path, name in [(root / 'docs/model-delivery-lock.json', 'model-delivery-lock.json'),
                   (batch / 'review-queue.json', 'review-queue.json')]:
    shutil.copyfile(path, packet / 'before' / name)
    assert path.read_bytes() == (packet / 'before' / name).read_bytes()
for name in names:
    shutil.copyfile(candidate / name, package / name)
    assert sha(package / name) == expected[name]
assert generate_board_json(package / names[0]) == manifest
outside = {name: value for name, value in baseline.items() if not name.startswith('Hangboards/' + slug + '/')}
assert len(outside) == 203
assert all(sha(root / name) == value for name, value in outside.items())

lock_path = root / 'docs/model-delivery-lock.json'
lock = load(lock_path)
entry = lock['migratedPackages'][slug]
entry.update(sourceSHA256=expected[names[0]], assetSHA256=expected[names[1]],
             descriptorSHA256=expected[names[2]],
             geometryAcceptance='pending revised human review #8: smoothed native shoulder and outline joins',
             nativeValidation='Native shoulder transitions and tangent-continuous outline joins; all 30 contact facts and published depths preserved. Fresh source/export and app proof retained with review #8.')
entry['assets']['assets/primary.usdz'].update(modelSHA256=entry['assetSHA256'],
                                            descriptorSHA256=entry['descriptorSHA256'])
spec = importlib.util.spec_from_file_location('delivery', root / 'scripts/verify-model-delivery.py')
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
checksums = delivery.checksum_manifest(root, lock['modelPackages'])
old_digest = lock['sha256Manifest']
digest = hashlib.sha256(checksums.encode()).hexdigest()
assert all(isinstance(x, str) for x in lock.get('sha256ManifestHistory', []))
lock.setdefault('sha256ManifestHistory', []).append(old_digest)
lock['supersededSha256Manifest'] = old_digest
lock['sha256Manifest'] = digest
save(lock_path, lock)
(batch / 'delivery-checksums.txt').write_text(checksums)
report = delivery.verify(root, lock)
assert report['passed'] and report['models'] == 58 and report['files'] == 135
save(scratch / 'delivery-validation.json', report)
save(batch / 'delivery-validation.json', report)
identity = {'owner': root.name, 'package': slug,
            'sourceSHA256': expected[names[0]], 'modelSHA256': expected[names[1]],
            'descriptorSHA256': expected[names[2]], 'manifestBytesUnchanged': True,
            'contactsUnchanged': 30, 'allOtherPackageFilesUnchanged': 203,
            'priorDeliveryDigest': old_digest, 'deliveryDigest': digest,
            'priorAssetCommit': 'ca5024c3b62f5ecc87e669e1ecab398e650b3890',
            'revisionBaseCommit': 'b097aa5ba34d55e69b9cdac73122b06774947a16',
            'humanGeometryAcceptance': 'pending revised review #8'}
save(scratch / 'integrated-package.json', identity)
print(json.dumps(identity, indent=2))
