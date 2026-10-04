import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-jagged'
batch = root / 'docs/source-audits/2026-09-29-remaining-cad'
slug = 'metolius-simulator-3d'
load = lambda p: json.loads(p.read_text())
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('packet', scratch / 'review-preparation/prepare_simulator_packet.py')
packet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packet)
assert sys.argv[1] in ('prepare', 'finalize')
state = 'one-by-one review in progress: first seven shown revisions accepted; revised Metolius Simulator 3-D #8 awaits human review after jagged feedback'

if sys.argv[1] == 'prepare':
    ios = load(scratch / 'ios/ios-summary.json')
    py = load(scratch / 'ios/python-test-report.json')
    installed = load(batch / 'installed-delivery-validation.json')
    assert ios['result'] == 'Passed' and ios['failedTests'] == 0 and py['exitCode'] == 0
    counts = re.search(r'(\d+) passed, (\d+) skipped', py['summary'])
    assert counts
    identity = load(scratch / 'integrated-package.json')
    tests = {'iOSPassed': ios['passedTests'], 'iOSSkipped': ios['skippedTests'],
             'pythonPassed': int(counts[1]), 'pythonSkipped': int(counts[2]),
             'separateNativeCompilerRegressionCases': 9, 'failures': 0}
    revision = {'package': slug, 'date': '2026-10-01', 'revision': 'rounded-outline-and-shoulder-transitions',
                'feedback': 'Jagged',
                **{k: identity[k] for k in ('sourceSHA256', 'modelSHA256', 'descriptorSHA256')},
                'report': slug + '/jagged-review/runtime-validation.json',
                'postIntegrationTests': tests, 'allOtherPackageFilesUnchanged': 203,
                'boardFactsAndContactIDsUnchanged': True,
                'geometryAcceptance': 'pending revised human review #8',
                'humanReviewRecord': slug + '/human-review.json',
                'limits': 'Rounded outline and positionally continuous shoulder joins; thickness94.1183246265mm is estimated and residual roof-normal changes reach6.77degrees. Representative app review only.'}
    bpath = batch / 'batch-validation.json'
    b = load(bpath)
    assert not any(x.get('revision') == revision['revision'] for x in b['reviewRevisions'])
    b['reviewRevisions'].append(revision)
    save(bpath, b)
    lpath = root / 'docs/model-delivery-lock.json'
    lock = load(lpath)
    entry = lock['migratedPackages'][slug]
    old_app = entry['nativeAppValidation']
    entry.setdefault('nativeAppHistory', []).append(old_app)
    entry['nativeAppValidation'] = str((batch / slug / 'jagged-review/app/after/validation.json').relative_to(root))
    item = dict(revision)
    item['report'] = str((batch / revision['report']).relative_to(root))
    item['humanReviewRecord'] = str((batch / revision['humanReviewRecord']).relative_to(root))
    item['priorDeliveryManifestSHA256'] = identity['priorDeliveryDigest']
    lock.setdefault('individualReviewRevisions', []).append(item)
    save(lpath, lock)
    qpath = batch / 'review-queue.json'
    text = qpath.read_text()
    qpath.write_text(packet.replace_json_value(text, ('reviewState',), state))
    save(scratch / 'revision-summary.json', {'revision': revision, 'installedCounts': installed['counts'],
                                           'deliveryDigest': identity['deliveryDigest']})
else:
    q = load(batch / 'review-queue.json')
    row = q['boards'][7]
    assert row['package'] == slug and row['number'] == 8
    human = load(batch / slug / 'human-review.json')
    assert human['question'] == 'Does this look smoother now?' and not human.get('answer')
    path = root / '.context/placid-badger/one-by-one-review.json'
    current = load(path)
    assert len(current['reviewed']) == 7
    current['current'] = row
    save(path, current)

print(json.dumps({'phase': sys.argv[1], 'humanReview': 'pending revised #8',
                  'firstSevenAccepted': True, 'nextBoardNotAdvanced': True}, indent=2))
