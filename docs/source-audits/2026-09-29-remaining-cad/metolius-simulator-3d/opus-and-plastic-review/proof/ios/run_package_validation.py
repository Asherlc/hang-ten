from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review/ios'
command = ['rtk', 'proxy', str(root / '.context/placid-badger/venv/bin/python'),
           '-m', 'hangboard_packages.cli', 'validate', '--root', 'Hangboards', '--final-inventory']
source = root / 'Hangboards/metolius-simulator-3d/metolius-simulator-3d.FCStd'
identity = {'owner': root.name, 'command': command, 'timeoutSeconds': 180,
            'sourceSHA256': hashlib.sha256(source.read_bytes()).hexdigest()}
started = time.monotonic()
with (scratch / 'package-validation.log').open('w') as log:
    result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                            env=dict(os.environ, TMPDIR=str(root / '.context/placid-badger/tmp') + '/'),
                            timeout=180)
identity.update(exitCode=result.returncode, elapsedSeconds=time.monotonic() - started)
(scratch / 'package-validation-command.json').write_text(json.dumps(identity, indent=2) + '\n')
assert result.returncode == 0
data = json.loads((scratch / 'package-validation.log').read_text())
assert len(data['boards']) == 64 and data['drafts'] == []
print(json.dumps({**identity, 'boards': 64, 'drafts': 0}))
