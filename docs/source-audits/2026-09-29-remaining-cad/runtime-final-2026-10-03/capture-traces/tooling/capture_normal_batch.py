"""Actual touch-driven app review, retaining failed DEBUG-preset evidence separately."""
from pathlib import Path
import json
import subprocess
import sys
import time

lane = Path(__file__).resolve().parent
number = int(sys.argv[1])
recipe = json.loads((lane / 'capture-recipes.json').read_text())['recipes'][str(number)]
helper = lane / 'app_review.py'
receipt = lane / f'capture-normal-batch-{number}.json'
assert not receipt.exists()
steps = []

def run(*args):
    command = ['rtk', 'proxy', 'python3', str(helper), *map(str, args)]
    record = {'command': command, 'startedAt': time.time()}
    steps.append(record)
    persist = lambda: receipt.write_text(json.dumps({'owner': 'placid-badger', 'number': number,
                                                     'steps': steps}, indent=2)+'\n')
    persist()
    result = subprocess.run(command, text=True, capture_output=True, timeout=120)
    record.update(exitCode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                  elapsedSeconds=time.time()-record['startedAt'])
    persist()
    print(result.stdout[-3000:], end='', flush=True)
    if result.returncode:
        print(result.stderr[-2000:], flush=True)
        raise SystemExit(result.returncode)

front = recipe['frontContact']
run('launch', number, front, '--telephoto')
run('capture', f'{number}-live-front')
for contact in recipe['faceContacts']:
    run('launch', number, contact, '--telephoto')
    run('capture', f'{number}-live-hold-{contact}')
run('launch', number, recipe['orbitContact'], '--telephoto')
for index in range(1, 4):
    run('orbit', f'{number}-live-horizontal-orbit-{index}')
run('launch', number, recipe['orbitContact'], '--telephoto')
run('orbit', f'{number}-live-top-oblique', '--start', '.23', '.72', '--end', '.83', '.22')
run('launch', number, front, '--landscape')
run('capture', f'{number}-live-landscape')
run('launch', number)
run('capture', f'{number}-live-unselected-train')
run('launch', number, front)
run('capture', f'{number}-live-normal-lens')
print(json.dumps({'number': number, 'touchDrivenBatchCompleted': True,
                  'visualAcceptance': 'Pending whole-frame inspection and human review'}), flush=True)
