"""Sequential whole app frames for one accepted root board; never reuse frames."""
from pathlib import Path
import json
import subprocess
import sys
import time

lane = Path(__file__).resolve().parent
number = int(sys.argv[1])
recipe = json.loads((lane / 'capture-recipes.json').read_text())['recipes'][str(number)]
helper = lane / 'app_review.py'
receipt = lane / f'capture-batch-{number}.json'
assert not receipt.exists()
steps = []

def run(*args):
    command = ['rtk', 'proxy', 'python3', str(helper), *map(str, args)]
    record = {'command': command, 'startedAt': time.time()}
    steps.append(record)
    receipt.write_text(json.dumps({'owner': 'placid-badger', 'number': number, 'steps': steps}, indent=2)+'\n')
    result = subprocess.run(command, text=True, capture_output=True, timeout=120)
    record.update(exitCode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                  elapsedSeconds=time.time()-record['startedAt'])
    receipt.write_text(json.dumps({'owner': 'placid-badger', 'number': number, 'steps': steps}, indent=2)+'\n')
    print(result.stdout[-3000:], end='', flush=True)
    if result.returncode:
        print(result.stderr[-2000:], flush=True)
        raise SystemExit(result.returncode)

front = recipe['frontContact']
run('launch', number, front, '--telephoto')
run('capture', f'{number}-front-canonical')
for view in ['front', 'side', 'top']:
    run('launch', number, recipe['orbitContact'], '--telephoto', '--view', view)
    run('capture', f'{number}-{view}')
for contact in recipe['faceContacts']:
    run('launch', number, contact, '--telephoto')
    run('capture', f'{number}-hold-{contact}')
run('launch', number, recipe['orbitContact'], '--telephoto')
run('orbit', f'{number}-actual-left-orbit')
run('orbit', f'{number}-actual-right-orbit', '--start', '.83', '.55', '--end', '.23', '.35')
run('launch', number, front)
run('capture', f'{number}-normal-lens')
print(json.dumps({'number': number, 'mechanicalBatchCompleted': True,
                  'visualAcceptance': 'Pending whole-frame inspection and human review'}), flush=True)
