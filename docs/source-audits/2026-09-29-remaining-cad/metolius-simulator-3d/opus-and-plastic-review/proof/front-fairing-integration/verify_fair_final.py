from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review'
batch = root / 'docs/source-audits/2026-09-29-remaining-cad'
slug = 'metolius-simulator-3d'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
run = lambda *args: subprocess.check_output(['rtk', 'proxy', *args], cwd=root, text=True, timeout=180)
head = 'b097aa5ba34d55e69b9cdac73122b06774947a16'
identity = load(scratch / 'integrated-package.json')
files = {'sourceSHA256': slug + '.FCStd', 'modelSHA256': 'assets/primary.usdz',
         'descriptorSHA256': 'assets/primary.model.json'}
assert all(sha(root / 'Hangboards' / slug / name) == identity[key] for key, name in files.items())
assert load(root / 'Hangboards' / slug / files['descriptorSHA256'])['modelSHA256'] == identity['modelSHA256']
assert not (root / 'Hangboards' / slug / 'board.json').exists()
baseline = load(scratch / 'all-hangboards-baseline.json')
outside = {p: h for p, h in baseline.items() if not p.startswith('Hangboards/' + slug + '/')}
assert len(outside) == 203 and all(sha(root / p) == h for p, h in outside.items())
assert set(run('git', 'diff', head, '--name-only', '--', 'Hangboards').splitlines()) == {
    'Hangboards/' + slug + '/' + name for name in files.values()}

spec = importlib.util.spec_from_file_location('packet', scratch / 'review-preparation/prepare_simulator_packet.py')
packet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packet)
queue_path = batch / 'review-queue.json'
old_queue = run('git', 'show', head + ':' + str(queue_path.relative_to(root)))
new_queue = queue_path.read_text()
old_spans, new_spans = packet.json_spans(old_queue), packet.json_spans(new_queue)
for i in range(21):
    if i == 7:
        continue
    a, b = old_spans[('boards', i)], new_spans[('boards', i)]
    assert old_queue[a[0]:a[1]] == new_queue[b[0]:b[1]], ('queue', i + 1)
row = json.loads(new_queue)['boards'][7]
assert row['sourceSHA256'] == identity['sourceSHA256']
assert 'not accepted' in row['humanReview']
lock_path = root / 'docs/model-delivery-lock.json'
old_lock = run('git', 'show', head + ':' + str(lock_path.relative_to(root)))
new_lock = lock_path.read_text()
a_spans, b_spans = packet.json_spans(old_lock), packet.json_spans(new_lock)
for name in json.loads(old_lock)['migratedPackages']:
    if name == slug:
        continue
    a, b = a_spans[('migratedPackages', name)], b_spans[('migratedPackages', name)]
    assert old_lock[a[0]:a[1]] == new_lock[b[0]:b[1]], ('lock', name)
assert json.loads(new_lock)['sha256Manifest'] == identity['deliveryDigest']
human = load(batch / slug / 'human-review.json')
assert human['question'] == 'Does this look right now?' and not human.get('answer')
old_audit = run('git', 'show', head + ':' + str((batch / slug / 'source-audit.md').relative_to(root)))
assert (batch / slug / 'source-audit.md').read_text().endswith(old_audit)
current = load(root / '.context/placid-badger/one-by-one-review.json')
assert len(current['reviewed']) == 7 and current['current']['number'] == 8

sys.path.insert(0, str(root / 'Tools/HangboardPackages/src'))
from hangboard_packages.cad_source import generate_board_json
assert generate_board_json(root / 'Hangboards' / slug / files['sourceSHA256']) == generate_board_json(
    scratch / 'review-preparation/plastic-tag-intermediate' / (slug + '.FCStd'))
spec = importlib.util.spec_from_file_location('delivery', root / 'scripts/verify-model-delivery.py')
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
delivery_check = delivery.verify(root, json.loads(new_lock))
assert delivery_check['passed'] and delivery_check['models'] == 58 and delivery_check['files'] == 135

covered_raw = set()
raw_count = 0
for name in ('jagged-review', 'opus-and-plastic-review'):
    base = batch / slug / name
    if name == 'opus-and-plastic-review':
        packet.verify(base, installed=True)
    for record in load(base / 'raw-retention.json')['byteIdenticalCopies']:
        retained = base / record['retained']
        assert sha(retained) == record['sha256'] and retained.stat().st_size == record['bytes']
        covered_raw.add(str(retained.relative_to(root)))
        raw_count += 1
changed = run('git', 'diff', head, '--name-only').splitlines()
checked = [p for p in changed if p not in covered_raw]
result = subprocess.run(['rtk', 'proxy', 'git', '--literal-pathspecs', 'diff', head, '--check', '--', *checked],
                        cwd=root, capture_output=True, text=True, timeout=180)
assert result.returncode == 0, result.stdout + result.stderr
cleanup = load(scratch / 'ios/verified-cleanup.json')
assert cleanup['exactSimulatorAbsent'] and cleanup['derivedDataRemoved'] and cleanup['xcresultRemoved']
assert load(scratch / 'opus-cleanup.json')['exactOwnedAdvisorArchived']
assert not (root / '.context/DerivedData').exists()
assert not (scratch / 'ios/placid-badger-simulator-plastic-tests.xcresult').exists()
report = {'status': 'pass', 'owner': root.name,
          **{k: identity[k] for k in files}, 'deliveryDigest': identity['deliveryDigest'],
          'otherPackageFilesUnchanged': 203, 'otherQueueRowsByteIdentical': 20,
          'otherMigrationLockEntriesByteIdentical': True, 'humanAcceptance': 'pending #8',
          'retainedRawCopiesVerified': raw_count, 'whitespaceCheckedFiles': len(checked),
          'whitespaceExclusions': 'Only exact raw-retention records verified by SHA256 and byte count.',
          'delivery': {'models': 58, 'files': 135}, 'cleanupVerified': True,
          'noOtherBoardReviewAdvanced': True}
(scratch / 'final-root-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
