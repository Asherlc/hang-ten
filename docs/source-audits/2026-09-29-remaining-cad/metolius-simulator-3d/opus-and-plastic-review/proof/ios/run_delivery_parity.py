from pathlib import Path
import hashlib, json, os, subprocess, time
from hangboard_packages.board_catalog import read_board_json

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review/ios'
destination = scratch / 'placid-badger-android-staging/Hangboards'
command = ['rtk', 'proxy', str(root / '.context/placid-badger/venv/bin/python'),
           'scripts/stage-board-packages.py', '--repository-root', str(root),
           '--destination', str(destination), '--target', 'android']
identity = {'owner': root.name, 'command': command, 'destination': str(destination),
            'timeoutSeconds': 180}
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
save(scratch / 'staging-command.json', identity)
started = time.monotonic()
with (scratch / 'staging.log').open('w') as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
        env=dict(os.environ, TMPDIR=str(root / '.context/placid-badger/tmp') + '/'), timeout=180)
identity.update(exitCode=result.returncode, elapsedSeconds=time.monotonic()-started)
save(scratch / 'staging-command.json', identity)
assert result.returncode == 0
installed = json.loads((root / 'docs/source-audits/2026-09-29-remaining-cad/installed-delivery-validation.json').read_text())
assert installed['passed']
rows = []
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for row in installed['packages']:
    slug = row['package']
    source, staged = root / 'Hangboards' / slug, destination / slug
    manifest = read_board_json(source)
    assert manifest == (staged / 'board.json').read_bytes()
    assert sha(staged / 'board.json') == row['manifestSHA256']
    assert not list(staged.glob('*.FCStd'))
    assert not (staged / 'suspension.json').exists()
    data = json.loads(manifest)
    for model in row['models']:
        media = next(p['media'] for p in data['presentations'] if p['id'] == model['presentationID'])
        assert sha(staged / media['assetPath']) == model['modelSHA256']
        assert sha(staged / media['descriptorPath']) == model['descriptorSHA256']
    rows.append({'package': slug, 'generatedManifestBytesMatchAppleAndSource': True,
                 'models': row['models'], 'authoringSourcesAbsent': True})
assert len(rows) == 64
validation = json.loads((scratch / 'package-validation.log').read_text())
assert len(validation['boards']) == 64 and validation['drafts'] == []
save(scratch / 'delivery-parity.json', {'status': 'passed', 'owner': root.name,
    'counts': installed['counts'], 'packages': rows, 'packageValidation': {'boards': 64, 'drafts': 0},
    'scope': 'Shared canonical Apple/Android staging; this checkout has no Android app runtime.'})
print(json.dumps({'status': 'passed', 'counts': installed['counts']}))
