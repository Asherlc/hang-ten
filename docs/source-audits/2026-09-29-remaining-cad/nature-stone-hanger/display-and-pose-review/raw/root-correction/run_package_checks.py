"""Check the frozen revised package once, retaining command and cleanup evidence."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time

ROOT = Path.cwd()
LANE = ROOT / '.context/placid-badger/nature-stone-review9/vertical-groove-correction'
SCRATCH = LANE / 'package-checks'
INPUTS = ROOT / '.context/placid-badger/nature-stone-review9/vertical-groove-ios/final-inputs.json'
PYTHON = ROOT / '.context/placid-badger/venv/bin/python'
FREECAD = Path('/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd')
NATIVE_PYTHON_PATH = ROOT / '.context/placid-badger/pxr311'
inputs = json.loads(INPUTS.read_text())
assert inputs['rootFinalHashReady'] is True
assert FREECAD.is_file() and NATIVE_PYTHON_PATH.is_dir()
SCRATCH.mkdir(exist_ok=True)
TEMP = SCRATCH / 'placid-badger-vertical-pytest-tmp'
assert not TEMP.exists(), 'Do not reuse another run temporary directory'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return {path: sha(ROOT / path) for path in inputs['packageSHA256']}


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


assert hashes() == inputs['packageSHA256']
tests = [
    'Tools/HangboardCAD/tests/test_board_manifest.py',
    'Tools/HangboardCAD/tests/test_cad_sidecars.py',
    'Tools/HangboardCAD/tests/test_native_cord_guides.py',
    'Tools/HangboardCAD/tests/test_native_cord_feature_extraction.py',
    'Tools/HangboardCAD/tests/test_native_cord_routes.py',
    'Tools/HangboardCAD/tests/test_native_cord_tightening.py',
    'Tools/HangboardCAD/tests/test_native_clearance_budget.py',
    'Tools/HangboardCAD/tests/test_native_path_search.py',
    'Tools/HangboardPackages/tests/test_board_catalog.py',
    'Tools/HangboardPackages/tests/test_cad_routed_cord.py',
    'Tools/HangboardPackages/tests/test_pose_camera_facing.py']
commands = {
    'package-validation': [str(PYTHON), '-m', 'hangboard_packages.cli', 'validate',
                           '--root', 'Hangboards', '--final-inventory'],
    'metadata-and-cord-tests': [str(PYTHON), '-m', 'pytest', '-q', *tests,
                              '--basetemp', str(TEMP)]}
for name, command in commands.items():
    receipt = SCRATCH / (name + '-command.json')
    log = SCRATCH / (name + '.log')
    assert not receipt.exists() and not log.exists(), 'Retain previous command evidence'
    record = {'owner': ROOT.name, 'command': ['rtk', 'proxy', *command],
              'timeoutSeconds': 300, 'packageSHA256': hashes(), 'status': 'running',
              'nativeToolchainEnvironment': {'HANGTEN_FREECAD_CMD': str(FREECAD),
                                             'HANGTEN_CAD_PYTHONPATH': str(NATIVE_PYTHON_PATH)},
              'ownedTemporaryDirectory': str(TEMP.relative_to(ROOT)) if name.endswith('tests') else None}
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    process = None
    started = time.monotonic()
    try:
        with log.open('w') as output:
            process = subprocess.Popen(record['command'], cwd=ROOT, start_new_session=True,
                                       stdout=output, stderr=subprocess.STDOUT,
                                       env=dict(os.environ, TMPDIR=str(ROOT / '.context/placid-badger/tmp') + '/',
                                                HANGTEN_FREECAD_CMD=str(FREECAD),
                                                HANGTEN_CAD_PYTHONPATH=str(NATIVE_PYTHON_PATH)))
            record.update(ownedPID=process.pid, ownedProcessGroup=process.pid)
            receipt.write_text(json.dumps(record, indent=2) + '\n')
            returncode = process.wait(timeout=record['timeoutSeconds'])
            record.update(exitCode=returncode, status='pass' if returncode == 0 else 'fail')
    except subprocess.TimeoutExpired:
        record.update(status='timeout', timeoutReached=True)
        raise
    except BaseException as error:
        record.update(status='fail', errorType=type(error).__name__)
        raise
    finally:
        if process is not None:
            if group_exists(process.pid):
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait(timeout=5)
            deadline = time.monotonic() + 5
            while group_exists(process.pid) and time.monotonic() < deadline:
                time.sleep(.1)
            record['ownedProcessGroupAbsent'] = not group_exists(process.pid)
        if name.endswith('tests'):
            if TEMP.exists(): shutil.rmtree(TEMP)
            record['ownedTemporaryDirectoryAbsent'] = not TEMP.exists()
        record.update(elapsedSeconds=time.monotonic() - started, packageSHA256After=hashes())
        record['packageBytesStable'] = record['packageSHA256'] == record['packageSHA256After']
        receipt.write_text(json.dumps(record, indent=2) + '\n')
    assert returncode == 0 and record['packageBytesStable'], name
    assert record['ownedProcessGroupAbsent'] is True
    if name == 'package-validation':
        data = json.loads(log.read_text())
        record.update(boards=len(data['boards']), drafts=len(data['drafts']))
        assert record['boards'] == 64 and record['drafts'] == 0
        receipt.write_text(json.dumps(record, indent=2) + '\n')
    else:
        text = log.read_text()
        result = re.search(r'(\d+) passed(?:, (\d+) skipped)? in ([\d.]+)s', text)
        assert result is not None, 'Cannot identify exact pytest counts'
        passed, skipped, elapsed = int(result[1]), int(result[2] or 0), float(result[3])
        assert passed > 0 and skipped == 0 and record['ownedTemporaryDirectoryAbsent']
        summary = {'status': 'pass', 'owner': ROOT.name, 'passed': passed, 'skipped': skipped,
                   'failed': 0, 'pytestElapsedSeconds': elapsed, 'packageBytesStable': True,
                   'packageSHA256': hashes(), 'ownedTemporaryDirectoryAbsent': True,
                   'ownedProcessGroupAbsent': True,
                   'command': {'path': str(receipt.relative_to(ROOT)), 'sha256': sha(receipt)},
                   'log': {'path': str(log.relative_to(ROOT)), 'sha256': sha(log)},
                   'scope': 'Current revised package; metadata, native groove/bore regressions, routed cord and pose/camera checks. Historical test runs are not summed.'}
        (SCRATCH / 'final-python-tests.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(record), flush=True)
