"""Root-only record application for the revised Stone Hanger geometry."""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import re

ROOT = Path.cwd()
BASE = ROOT / '.context/placid-badger/nature-stone-review9'
LANE = BASE / 'vertical-groove-correction'
AUDIT = 'docs/source-audits/2026-09-29-remaining-cad'
PACKET = AUDIT + '/nature-stone-hanger/display-and-pose-review'
SLUG = 'nature-stone-hanger'

# Retain the already reviewed lexical JSON editors without executing the
# superseded record updater. They preserve other package entries verbatim.
tree = ast.parse((BASE / 'apply_final_records.py').read_text())
names = {'sha', 'value_spans', 'replace_value', 'append_array', 'add_top_level_value'}
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in functions} == names
exec(compile(ast.Module(body=functions, type_ignores=[]), '<retained-json-editors>', 'exec'))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('build', 'apply'))
parser.add_argument('--builder', type=Path, required=True)
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--update', type=Path, required=True)
args = parser.parse_args()
prep = load_module('vertical_groove_packet', args.builder.resolve())
config = json.loads(args.config.read_text())
proof = prep.final_check(config)
prep.verify(ROOT / PACKET)
update = json.loads(args.update.read_text())
assert update['rootFinalReviewConfirmed'] is True
assert update['identity'] == config['identity']
identity = update['identity']
revision = update['revision']
assert revision['package'] == SLUG
assert revision['nativeBodyGeometryChanged'] is True
assert revision['boardFactsAndContactIDsUnchanged'] is True
assert revision['geometryAcceptance'] == 'pending one-by-one user review'
assert all(revision[k] == identity[k] for k in ('sourceSHA256', 'modelSHA256', 'descriptorSHA256'))
assert revision['suspensionSHA256'] == identity['sidecarSHA256']

baseline = json.loads((BASE / 'other-packages-baseline.json').read_text())
assert len(baseline['files']) == 202
assert all(sha(ROOT / p['path']) == p['sha256'] for p in baseline['files'])
paths = {'model-delivery-lock.json': 'docs/model-delivery-lock.json',
         **{name: AUDIT + '/' + name for name in (
             'review-queue.json', 'batch-validation.json', 'delivery-checksums.txt',
             'delivery-validation.json', 'installed-delivery-validation.json')}}
before = {name: (ROOT / path).read_text() for name, path in paths.items()}
assert all(text == (BASE / 'before-global-records' / name).read_text()
           for name, text in before.items())
lock = json.loads(before['model-delivery-lock.json'])
delivery = load_module('vertical_groove_delivery', ROOT / 'scripts/verify-model-delivery.py')
manifest = delivery.checksum_manifest(ROOT, lock['modelPackages'])
digest = hashlib.sha256(manifest.encode()).hexdigest()
old_lines = before['delivery-checksums.txt'].splitlines(keepends=True)
new_lines = manifest.splitlines(keepends=True)
assert len(old_lines) == len(new_lines)
changed = [b.split('  ', 1)[1].strip() for a, b in zip(old_lines, new_lines) if a != b]
assert set(changed) == {
    'Hangboards/' + SLUG + '/' + SLUG + '.FCStd',
    'Hangboards/' + SLUG + '/suspension.json',
    'Hangboards/' + SLUG + '/assets/primary.usdz',
    'Hangboards/' + SLUG + '/assets/primary.model.json'}

entry = lock['migratedPackages'][SLUG]
entry.update(update['lockEntry'])
assert entry['sourceSHA256'] == identity['sourceSHA256']
assert entry['suspensionSHA256'] == identity['sidecarSHA256']
assert entry['assetSHA256'] == identity['modelSHA256']
assert entry['descriptorSHA256'] == identity['descriptorSHA256']
asset = entry['assets']['assets/primary.usdz']
assert asset['modelSHA256'] == identity['modelSHA256']
assert asset['descriptorSHA256'] == identity['descriptorSHA256']
text = replace_value(before['model-delivery-lock.json'], ('migratedPackages', SLUG), entry)
if lock['sha256Manifest'] not in lock['sha256ManifestHistory']:
    text = append_array(text, ('sha256ManifestHistory',), lock['sha256Manifest'])
text = replace_value(text, ('sha256Manifest',), digest)
text = append_array(text, ('individualReviewRevisions',), revision)
new_lock = json.loads(text)
assert new_lock['modelPackages'] == lock['modelPackages']
assert set(new_lock['migratedPackages']) == set(lock['migratedPackages'])
old_spans = value_spans(before['model-delivery-lock.json'])
new_spans = value_spans(text)
other_lock_slugs = [s for s in lock['migratedPackages'] if s != SLUG]
for slug in other_lock_slugs:
    key = ('migratedPackages', slug)
    a, b = old_spans[key]; c, d = new_spans[key]
    assert before['model-delivery-lock.json'][a:b] == text[c:d], slug
verified = delivery.verify(ROOT, new_lock)
assert verified['passed'] and verified['models'] == len(lock['modelPackages'])
assert verified['files'] == len(new_lines)

queue = json.loads(before['review-queue.json'])
assert queue['boards'][8]['number'] == 9 and queue['boards'][8]['package'] == SLUG
row = queue['boards'][8]
row.update(update['queueEntry'])
assert row['humanReview'] == 'pending'
assert row['sourceSHA256'] == identity['sourceSHA256']
assert row['suspensionSHA256'] == identity['sidecarSHA256']
assert row['presentations']['primary']['modelSHA256'] == identity['modelSHA256']
assert row['presentations']['primary']['descriptorSHA256'] == identity['descriptorSHA256']
queue_text = replace_value(before['review-queue.json'], ('boards', 8), row)
old_spans = value_spans(before['review-queue.json']); new_spans = value_spans(queue_text)
for i in range(len(queue['boards'])):
    if i == 8: continue
    a, b = old_spans[('boards', i)]; c, d = new_spans[('boards', i)]
    assert before['review-queue.json'][a:b] == queue_text[c:d]
batch_revision = dict(revision, report=update['batchReport'])
batch_text = append_array(before['batch-validation.json'], ('reviewRevisions',), batch_revision)
installed = update['installedDeliveryUpdate']
assert installed['humanAcceptance'] == 'pending'
assert installed['sourceSHA256'] == identity['sourceSHA256']
assert installed['suspensionSHA256'] == identity['sidecarSHA256']
assert installed['modelSHA256'] == identity['modelSHA256']
assert installed['descriptorSHA256'] == identity['descriptorSHA256']
assert installed['binaryBytesMatch'] and installed['generatedManifestBytesMatchSource']
installed_text = add_top_level_value(before['installed-delivery-validation.json'],
                                     'stoneHangerReview9', installed)
human_path = AUDIT + '/nature-stone-hanger/human-review.json'
assert not (ROOT / human_path).exists()
human = json.loads((ROOT / PACKET / 'human-review-proposal.json').read_text())
assert human['status'] == 'pending' and human['identity'] == identity
human.update(update['humanReviewRecord'])
assert human['status'] == 'pending'
outputs = {
    paths['model-delivery-lock.json']: text,
    paths['review-queue.json']: queue_text,
    paths['batch-validation.json']: batch_text,
    paths['delivery-checksums.txt']: manifest,
    paths['delivery-validation.json']: json.dumps(verified, indent=2) + '\n',
    paths['installed-delivery-validation.json']: installed_text,
    human_path: json.dumps(human, indent=2) + '\n'}
stage = LANE / 'final-records-stage'
if args.action == 'build':
    assert not stage.exists(), 'Preserve historical stages'
    stage.mkdir()
    for relative, content in outputs.items():
        target = stage / relative; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    receipt = {'status': 'pass', 'owner': ROOT.name, 'identity': identity,
               'humanAcceptance': 'pending', 'otherPackageFilesUnchanged': 202,
               'otherLockEntriesUnchanged': len(other_lock_slugs),
               'otherQueueRowsUnchanged': len(queue['boards']) - 1,
               'changedDeliveryLines': changed, 'delivery': verified,
               'packetProofSHA256': sha(ROOT / PACKET / 'runtime-validation.json'),
               'originalGlobals': {relative: sha(ROOT / relative) for relative in paths.values()},
               'outputs': {relative: sha(stage / relative) for relative in outputs}}
    (stage / 'record-update-proof.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'staged', 'files': len(outputs), 'deliveryDigest': digest,
                      'otherLockEntries': len(other_lock_slugs), 'humanAcceptance': 'pending'}))
else:
    receipt = json.loads((stage / 'record-update-proof.json').read_text())
    assert receipt['identity'] == identity
    for relative, content in outputs.items():
        target = stage / relative
        assert target.read_text() == content and sha(target) == receipt['outputs'][relative]
    assert all(sha(ROOT / relative) == expected for relative, expected in receipt['originalGlobals'].items())
    for relative in outputs:
        (ROOT / relative).write_bytes((stage / relative).read_bytes())
    assert all(sha(ROOT / relative) == expected for relative, expected in receipt['outputs'].items())
    receipt = dict(receipt, status='pass-applied')
    (LANE / 'applied-records-proof.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'applied', 'files': len(outputs), 'humanAcceptance': 'pending'}))
