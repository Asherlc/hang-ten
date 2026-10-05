from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-jagged'
batch = root / 'docs/source-audits/2026-09-29-remaining-cad'
slug = 'metolius-simulator-3d'
packet = batch / slug / 'jagged-review'
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
run = lambda *a: subprocess.check_output(['rtk', 'proxy', *a], cwd=root, timeout=60)
identity = load(scratch / 'integrated-package.json')
names = {'sourceSHA256': slug + '.FCStd', 'modelSHA256': 'assets/primary.usdz',
         'descriptorSHA256': 'assets/primary.model.json'}
for key, name in names.items():
    assert sha(root / 'Hangboards' / slug / name) == identity[key]
    assert sha(packet / 'candidate' / name) == identity[key]
    prior_git = run('git', 'show', 'b097aa5ba34d55e69b9cdac73122b06774947a16:Hangboards/' + slug + '/' + name)
    prior = packet / 'before' / name
    if prior_git.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        fields = prior_git.decode().splitlines()
        assert sha(prior) == next(x.removeprefix('oid sha256:') for x in fields if x.startswith('oid sha256:'))
        assert prior.stat().st_size == int(next(x.removeprefix('size ') for x in fields if x.startswith('size ')))
    else:
        assert prior.read_bytes() == prior_git
before_archive = packet / 'before' / names['sourceSHA256']
after_archive = root / 'Hangboards' / slug / names['sourceSHA256']
def raw_manifest(path):
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        xml = ET.fromstring(z.read('Document.xml'))
    prop = xml.find('.//Property[@name="HangTenBoardManifest"]')
    assert prop is not None
    child = prop.find('String')
    assert child is not None
    return child.attrib['value'].encode()
assert raw_manifest(before_archive) == raw_manifest(after_archive)
baseline = load(scratch / 'independent-validation/all-hangboards-baseline.json')['files']
outside = {p: row for p, row in baseline.items() if not p.startswith('Hangboards/' + slug + '/')}
assert len(outside) == 203
assert all(sha(root / p) == row['sha256'] for p, row in outside.items())
current = {str(p.relative_to(root)) for p in (root / 'Hangboards').rglob('*') if p.is_file()}
assert current == set(baseline)
assert not (root / 'Hangboards' / slug / 'board.json').exists()
compiler = root / 'Tools/HangboardCAD/compile_board.py'
assert sha(compiler) == 'f4c0d4c2a9c79c02d349be2f71a14962fde3c5c2fa13b24b0b34d425272fc50d'
uv_sources = []
for p in sorted((root / 'Hangboards').glob('*/*.FCStd')):
    with zipfile.ZipFile(p) as z:
        if b'HangTenUVNodeSurfaceNormals' in z.read('Document.xml'):
            uv_sources.append(str(p.relative_to(root)))
assert uv_sources == ['Hangboards/' + slug + '/' + slug + '.FCStd']

queue = load(batch / 'review-queue.json')
old_queue = load(packet / 'before/review-queue.json')
assert len(queue['boards']) == 21
assert all(a == b for a, b in zip(queue['boards'], old_queue['boards']) if a['number'] != 8)
accepted = {}
for row in queue['boards'][:7]:
    p = batch / row['package'] / 'human-review.json'
    assert row['humanReview'].startswith('reviewed')
    assert p.read_bytes() == run('git', 'show', 'b097aa5ba34d55e69b9cdac73122b06774947a16:' + str(p.relative_to(root)))
    accepted[row['package']] = sha(p)
added = run('git', 'diff', '--diff-filter=A', '--name-only',
            'd0e4e95191e4a76822815bb4eeef3a32caa6fea0',
            '583a2d08ec45909d62c426c0e7f3f7ec4384c7c7', '--', 'Hangboards').decode().splitlines()
added_native = {Path(p).parts[1] for p in added if p.endswith('.FCStd')}
assert added_native == {row['package'] for row in queue['boards']} and len(added_native) == 21
human = load(batch / slug / 'human-review.json')
assert human['question'] == 'Does this look smoother now?'
assert not human.get('answer') and not human.get('acceptedScope')
assert human['sourceSHA256'] == identity['sourceSHA256']
state = load(root / '.context/placid-badger/one-by-one-review.json')
assert len(state['reviewed']) == 7 and state['current'] == queue['boards'][7]
for rel, digest in human['shownImages'].items():
    assert sha(batch / slug / rel) == digest
for rel, row in load(packet / 'retained-files.json')['files'].items():
    assert sha(packet / rel) == row['sha256']
for row in load(packet / 'raw-retention.json')['byteIdenticalCopies']:
    assert sha(packet / row['retained']) == row['sha256']
assert (batch / slug / 'source-audit.md').read_bytes().endswith((packet / 'before/source-audit.md').read_bytes())

lock = load(root / 'docs/model-delivery-lock.json')
assert all(isinstance(d, str) for d in lock['sha256ManifestHistory'])
spec = importlib.util.spec_from_file_location('delivery', root / 'scripts/verify-model-delivery.py')
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
verified = delivery.verify(root, lock)
assert verified['passed'] and verified['models'] == 58 and verified['files'] == 135
assert hashlib.sha256(delivery.checksum_manifest(root, lock['modelPackages']).encode()).hexdigest() == lock['sha256Manifest'] == identity['deliveryDigest']
assert lock['migratedPackages'][slug]['geometryAcceptance'] == 'pending revised human review #8'
ios = load(scratch / 'ios/ios-summary.json')
python = load(scratch / 'ios/python-test-report.json')
assert ios['result'] == 'Passed' and ios['failedTests'] == 0 and python['exitCode'] == 0
parity = load(scratch / 'ios/delivery-parity.json')
assert parity['status'] == 'passed' and len(parity['packages']) == 64
cleanup = load(scratch / 'ios/verified-cleanup.json')
devices = json.loads(run('xcrun', 'simctl', 'list', 'devices', '--json'))
assert not any(d['udid'] == cleanup['simulator'] for g in devices['devices'].values() for d in g)
assert not (root / '.context/DerivedData').exists()
assert not (scratch / 'ios/placid-badger-simulator-jagged-tests.xcresult').exists()
report = {
    'verifiedAtUTC': datetime.now(timezone.utc).isoformat(), 'status': 'passed', 'owner': root.name,
    **{key: identity[key] for key in names}, 'compilerSHA256': sha(compiler),
    'unrelatedPackageFilesUnchanged': 203, 'unchangedRawManifest': True,
    'firstSevenHumanReviewFilesUnchanged': accepted,
    'migrationOnlyQueueEntries': 21, 'onlyUVOptInSource': uv_sources,
    'deliveryModels': 58, 'lockedFiles': 135, 'deliveryDigest': lock['sha256Manifest'],
    'pythonSummary': python['summary'], 'iOSPassed': ios['passedTests'], 'iOSSkipped': ios['skippedTests'],
    'separateNativeRegressionCases': 9, 'packageParity': parity['counts'],
    'retainedPacketHashesVerified': True, 'shownImageHashesVerified': True,
    'exactOwnedSimulatorDeleted': cleanup['simulator'], 'derivedDataAndTestBundleRemoved': True,
    'humanAcceptance': 'pending revised #8', 'nextBoardNotAdvanced': True,
}
(scratch / 'final-closure.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
