from pathlib import Path
import json
import os
import subprocess
import time

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-plastic-review/ios'
uid = (scratch / 'simulator-ready').read_text().strip()
result = scratch / 'placid-badger-simulator-plastic-tests.xcresult'
assert not result.exists()
command = ['xcodebuild', '-project', 'HangTen.xcodeproj', '-scheme', 'HangTen',
           '-configuration', 'Debug', '-destination', 'platform=iOS Simulator,id=' + uid,
           '-derivedDataPath', '.context/DerivedData', '-parallel-testing-enabled', 'NO',
           '-only-testing:HangTenTests', '-collect-test-diagnostics', 'never', '-resultBundlePath', str(result),
           'test-without-building']
identity = {'owner': 'placid-badger', 'simulator': uid, 'command': command,
            'timeoutSeconds': 900, 'resultBundle': str(result)}
(scratch / 'ios-test-command.json').write_text(json.dumps(identity, indent=2) + '\n')
env = dict(os.environ, TMPDIR=str(root / '.context/placid-badger/tmp') + '/')
started = time.monotonic()
with (scratch / 'ios-tests.log').open('w') as log:
    completed = subprocess.run(['rtk', 'proxy', *command], stdout=log,
                               stderr=subprocess.STDOUT, env=env, timeout=900)
identity.update(exitCode=completed.returncode, elapsedSeconds=time.monotonic() - started)
(scratch / 'ios-test-command.json').write_text(json.dumps(identity, indent=2) + '\n')
if result.exists():
    summary = subprocess.check_output(['rtk', 'proxy', 'xcrun', 'xcresulttool', 'get',
                                      'test-results', 'summary', '--path', str(result)],
                                     text=True, timeout=30)
    (scratch / 'ios-summary.json').write_text(summary)
    print(summary, flush=True)
raise SystemExit(completed.returncode)
