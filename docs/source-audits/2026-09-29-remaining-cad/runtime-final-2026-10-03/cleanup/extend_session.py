"""Extend the exact owned session; always resume its installed cleanup trap."""
from pathlib import Path
import atexit
import json
import os
import signal
import subprocess
import time

lane = Path(__file__).resolve().parent
root = Path.cwd()
owner = json.loads((lane / 'ownership.json').read_text())
assert owner['owner'] == root.name == 'placid-badger'
uid = owner['simulatorUUID']
assert uid in (root / '.context/paseo-owned-simulators').read_text().splitlines()
pid = 66257
command = subprocess.check_output(['rtk', 'proxy', 'ps', '-p', str(pid), '-o', 'command='], text=True).strip()
assert command == '/opt/homebrew/bin/zsh .context/placid-badger/runtime-final-2026-10-03/ios-session.zsh', command
receipt = lane / 'session-extension.json'
assert not receipt.exists()
record = {'owner': root.name, 'simulatorUUID': uid, 'originalOwnedSessionPID': pid,
          'extensionGuardianPID': os.getpid(), 'originalCleanupTrap': 'ios-session.zsh',
          'startedAt': time.time(), 'maximumExtensionSeconds': 5400,
          'originalSessionPaused': False, 'cleanupResumed': False}

def persist():
    receipt.write_text(json.dumps(record, indent=2) + '\n')

def cleanup():
    (lane / 'finish-ios-session').touch()
    if record['originalSessionPaused']:
        try:
            os.kill(pid, signal.SIGCONT)
            record['cleanupResumed'] = True
        except ProcessLookupError:
            record['originalAlreadyExited'] = True
    record['finishedAt'] = time.time()
    persist()

def interrupt(signum, _):
    raise SystemExit(128 + signum)

atexit.register(cleanup)
signal.signal(signal.SIGTERM, interrupt)
signal.signal(signal.SIGINT, interrupt)
persist()
os.kill(pid, signal.SIGSTOP)
record['originalSessionPaused'] = True
persist()
print(json.dumps({'owner': root.name, 'ownedSessionLifetimeExtended': True,
                  'originalCleanupTrapRetained': True, 'simulatorUUID': uid}), flush=True)
deadline = time.monotonic() + 5400
while not (lane / 'finish-ios-session').exists():
    if time.monotonic() >= deadline:
        raise TimeoutError('Owned review lifetime extension ended')
    time.sleep(2)
