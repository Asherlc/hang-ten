"""Run one bounded verification command with exact workspace ownership."""
from pathlib import Path
import datetime
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path.cwd()
LANE = Path(__file__).resolve().parent
OWNER = ROOT.name
config = json.loads(Path(sys.argv[1]).read_text())
name = config['name']
assert name.startswith(OWNER + '-') and '/' not in name
receipt = LANE / (name + '-command.json')
log = LANE / (name + '.log')
temporary = LANE / (name + '-tmp')
assert not receipt.exists() and not log.exists() and not temporary.exists()
command = ['rtk', 'proxy', *config['command']]
record = {'workspaceOwner': OWNER, 'command': command,
          'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'timeoutSeconds': config.get('timeoutSeconds', 300),
          'ownedTemporaryDirectory': str(temporary.relative_to(ROOT)),
          'status': 'running', 'ownedProcessGroup': None}
process = None
rc = 1
started = time.monotonic()

def persist():
    receipt.write_text(json.dumps(record, indent=2) + '\n')

def exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False

def interrupt(signum, frame):
    raise SystemExit(128 + signum)

handlers = {s: signal.signal(s, interrupt) for s in (signal.SIGINT, signal.SIGTERM)}
try:
    temporary.mkdir()
    persist()
    environment = dict(os.environ, TMPDIR=str(temporary) + '/')
    environment.update(config.get('environment', {}))
    with log.open('w') as output:
        process = subprocess.Popen(command, cwd=ROOT, env=environment,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        record['ownedProcessGroup'] = process.pid
        persist()
        rc = process.wait(timeout=record['timeoutSeconds'])
except BaseException as error:
    rc = 124 if isinstance(error, subprocess.TimeoutExpired) else (
        int(error.code) if isinstance(error, SystemExit) and isinstance(error.code, int) else 1)
    record['error'] = {'type': type(error).__name__, 'message': str(error),
                       'traceback': traceback.format_exc()}
finally:
    for signum in handlers:
        signal.signal(signum, signal.SIG_IGN)
    cleanup_error = None
    try:
        if process is not None:
            if exists(process.pid):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=15)
            deadline = time.monotonic() + 10
            while exists(process.pid) and time.monotonic() < deadline:
                time.sleep(.1)
            assert not exists(process.pid), 'Owned process group still exists'
        record['ownedProcessGroupAbsent'] = True
        if temporary.exists():
            shutil.rmtree(temporary)
        assert not temporary.exists()
        record['ownedTemporaryDirectoryAbsent'] = True
    except BaseException as error:
        cleanup_error = traceback.format_exc()
        record['cleanupError'] = cleanup_error
        if rc == 0:
            rc = 1
    record.update(exitCode=rc, status='pass' if rc == 0 else 'fail',
                  elapsedSeconds=time.monotonic() - started)
    persist()
    for signum, handler in handlers.items():
        signal.signal(signum, handler)
print(json.dumps(record), flush=True)
if rc:
    print(log.read_text()[-5000:], file=sys.stderr)
raise SystemExit(rc)
