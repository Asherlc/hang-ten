"""Actual existing-plan work/rest states; no authored plan or clock changes."""
from pathlib import Path
import json
import subprocess
import sys
import time

lane = Path(__file__).resolve().parent
number = int(sys.argv[1])
orientation = sys.argv[2] if len(sys.argv) > 2 else 'landscape'
prefix = f'{number}-workout-{orientation}'
receipt = lane / (prefix+'-actions.json')
assert not receipt.exists()
helper = lane / 'app_review.py'
steps = []

def run(*args):
    command = ['rtk', 'proxy', 'python3', str(helper), *map(str, args)]
    record = {'command': command, 'startedAt': time.time()}
    steps.append(record)
    receipt.write_text(json.dumps({'owner': 'placid-badger', 'number': number, 'steps': steps}, indent=2)+'\n')
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    record.update(exitCode=result.returncode, elapsedSeconds=time.time()-record['startedAt'],
                  stdout=result.stdout, stderr=result.stderr)
    receipt.write_text(json.dumps({'owner': 'placid-badger', 'number': number, 'steps': steps}, indent=2)+'\n')
    if args[0] != 'dump':
        print(result.stdout[-2000:], end='', flush=True)
    if result.returncode:
        print(result.stderr[-2000:], flush=True)
        raise SystemExit(result.returncode)
    return result.stdout

def rows():
    run('dump')
    return json.loads((lane/'app-captures/latest-accessibility.json').read_text())

def wait_for(predicate, seconds=30):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        current = rows()
        if predicate(current):
            return current
        time.sleep(.5)
    run('capture', prefix+'-state-failure', '--raw')
    raise RuntimeError('Actual workout state did not reach expected source step')

def is_step(current, step):
    return any(r.get('AXUniqueId') == 'workout.routinePicker' and
               f'current step {step}:' in str(r.get('AXLabel')) for r in current)

run('launch', number, '--plan', 'research.abrahangs', '--step', 17, '--autostart',
    *(['--landscape'] if orientation == 'landscape' else []))
current = rows()
if any(r.get('type') == 'Button' and r.get('AXLabel') in ('Start', 'Resume') for r in current):
    label = next(r['AXLabel'] for r in current if r.get('type') == 'Button' and r.get('AXLabel') in ('Start','Resume'))
    run('tap', prefix+'-start', '--label', label)
wait_for(lambda r: is_step(r, 17) and any(x.get('AXUniqueId') == 'workout.timer' and
          x.get('AXLabel') in ('00:07', '00:06', '00:05', '00:04') for x in r))
run('tap', prefix+'-work-paused', '--label', 'Pause')
current = rows()
assert is_step(current, 17)
if orientation == 'portrait':
    run('scroll', 'up')
run('capture', prefix+'-work-highlight')
current = rows()
label = next(r['AXLabel'] for r in current if r.get('type') == 'Button' and r.get('AXLabel') in ('Start','Resume'))
run('tap', prefix+'-resume', '--label', label)
wait_for(lambda r: is_step(r, 18) and any(x.get('AXUniqueId') == 'workout.timer' and
          str(x.get('AXLabel','')).startswith('00:4') for x in r))
run('tap', prefix+'-rest-paused', '--label', 'Pause')
if orientation == 'portrait':
    run('scroll', 'up')
run('capture', prefix+'-rest-preview')
current = rows()
assert is_step(current, 18)
print(json.dumps({'number': number, 'orientation': orientation,
                  'sourcePlanID': 'research.abrahangs', 'sourceWorkStep': 17, 'sourceRestStep': 18,
                  'actualWorkAndRestCaptured': True, 'visualColorAcceptance': 'Pending whole-frame inspection'}), flush=True)
