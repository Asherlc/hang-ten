from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review'
before = scratch / 'before'
before.mkdir()
package = root / 'Hangboards/metolius-simulator-3d'
audit = root / 'docs/source-audits/2026-09-29-remaining-cad/metolius-simulator-3d'
names = ['metolius-simulator-3d.FCStd', 'assets/primary.usdz', 'assets/primary.model.json']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = ['8fa07c203943d849101ba80926fb6c1d69c2ace7dff982a68f6e8a6476f618f7',
            'c87d2acf4226a3f31ce11fd2e086b891b3608bef58e74f40d50c82f2318e8628',
            '3aba3cf597f09d23339940711b6a13efe008431a60a8f84d292c173335c7da9d']
for name, digest in zip(names, expected):
    assert sha(package / name) == digest
    target = before / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(package / name, target)
for path in [audit / 'human-review.json', audit / 'source-audit.md',
             audit.parent / 'review-queue.json', root / 'docs/model-delivery-lock.json']:
    shutil.copyfile(path, before / path.name)
baseline = {str(p.relative_to(root)): sha(p) for p in sorted((root / 'Hangboards').rglob('*')) if p.is_file()}
(scratch / 'all-hangboards-baseline.json').write_text(json.dumps(baseline, indent=2) + '\n')
old = json.loads((scratch / 'before-manifest.json').read_text())
new = json.loads(json.dumps(old))
assert len(old['contacts']) == 30
assert 'surfaceFinish' not in old['presentations'][0]['media']['display']
new['presentations'][0]['media']['display']['surfaceFinish'] = 'plastic'
(scratch / 'after-manifest.json').write_text(json.dumps(new, indent=2) + '\n')
command = ['rtk', 'proxy', sys.executable, 'Tools/HangboardCAD/set_board_manifest.py',
           '--package', 'metolius-simulator-3d', str(scratch / 'after-manifest.json')]
with (scratch / 'manifest-update.log').open('wb') as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=60)
assert result.returncode == 0
sys.path.insert(0, str(root / 'Tools/HangboardPackages/src'))
from hangboard_packages import cad_source
board = cad_source.load_board(package / names[0])
after = cad_source.board_to_manifest(board)
assert after == new
normalized = json.loads(json.dumps(after))
assert normalized['presentations'][0]['media']['display'].pop('surfaceFinish') == 'plastic'
assert normalized == old
with zipfile.ZipFile(before / names[0]) as z:
    members_before = {name: z.read(name) for name in z.namelist()}
with zipfile.ZipFile(package / names[0]) as z:
    members_after = {name: z.read(name) for name in z.namelist()}
assert members_before.keys() == members_after.keys()
changed = [name for name in members_before if members_before[name] != members_after[name]]
assert changed == ['Document.xml']
breps = [name for name in members_before if name.lower().endswith('.brp')]
assert len(breps) == 387
for name, digest in zip(names[1:], expected[1:]):
    assert sha(package / name) == digest
outside = {name: digest for name, digest in baseline.items() if not name.startswith('Hangboards/metolius-simulator-3d/')}
assert len(outside) == 203 and all(sha(root / name) == digest for name, digest in outside.items())
assert not (package / 'board.json').exists()
report = {
    'recordedAtUTC': datetime.now(timezone.utc).isoformat(), 'owner': root.name,
    'status': 'pass', 'command': command, 'exitCode': result.returncode,
    'previousSourceSHA256': expected[0], 'sourceSHA256': sha(package / names[0]),
    'modelSHA256': expected[1], 'descriptorSHA256': expected[2],
    'onlyChangedArchiveMember': 'Document.xml', 'unchangedBRepMembers': len(breps),
    'allNonDocumentMembersByteIdentical': True, 'geometryChanged': False,
    'onlyChangedManifestField': '/presentations/0/media/display/surfaceFinish',
    'surfaceFinish': 'plastic', 'unchangedContactIDsAndFacts': 30,
    'allOtherManifestFieldsUnchanged': True, 'allOtherPackageFilesUnchanged': 203,
    'runtimePaletteSource': 'HangTen/Models/BoardModelRealityTypes.swift plasticMaterial',
    'paletteScope': 'Existing mint app display palette, not a manufacturer color claim.',
    'authorization': 'User: It should be tagged as plastic so it gets colored',
    'geometryProofScope': 'Exact BRep/export preservation carries the hash-bound geometry checks of8fa07c to this metadata-only source; no new native geometry is authored.',
    'humanAcceptance': 'pending revised review #8',
}
(scratch / 'metadata-preservation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
