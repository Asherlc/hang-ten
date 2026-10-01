from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-simulator-3d-jagged/ios'
phase = sys.argv[1]
assert phase in ('before', 'after')
out = scratch / (phase + '-captures')
out.mkdir(exist_ok=True)
uid = (scratch / 'simulator-ready').read_text().strip()
app = root / '.context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app'
package = root / 'Hangboards/metolius-simulator-3d'
commands = []
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_hash = sha(package / 'metolius-simulator-3d.FCStd')
installed = Path(subprocess.check_output(['rtk', 'proxy', 'xcrun', 'simctl', 'get_app_container',
                                         uid, 'com.hangten.training', 'app'], text=True).strip())
assert (app / 'HangTen').read_bytes() == (installed / 'HangTen').read_bytes()
assert (app / 'Hangboards/metolius-simulator-3d/board.json').read_bytes() == (
    installed / 'Hangboards/metolius-simulator-3d/board.json').read_bytes()
manifest = json.loads((installed / 'Hangboards/metolius-simulator-3d/board.json').read_text())
expected_contact_ids = {x['id'] for x in manifest['contacts']}
assert len(expected_contact_ids) == 30

def run(*args, env=None):
    cmd = ['rtk', 'proxy', *map(str, args)]
    commands.append(cmd)
    return subprocess.check_output(cmd, text=True, env=env, timeout=120)

def flatten(nodes):
    rows = []
    for node in nodes:
        if node.get('AXLabel') or node.get('AXUniqueId'):
            rows.append({k: node.get(k) for k in ('type', 'AXLabel', 'AXUniqueId', 'AXValue', 'frame')})
        rows.extend(flatten(node.get('children', [])))
    return rows

def ready(contact):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        rows = flatten(json.loads(run('/opt/homebrew/bin/axe', 'describe-ui', '--udid', uid)))
        ids = {r['AXUniqueId'] for r in rows if r['AXUniqueId']}
        assert 'boardModel.unavailable' not in ids
        if ('boardDetail.selectedHold.' + contact in ids and 'boardModel.loading' not in ids
                and any(i.startswith('boardModel.contact.') for i in ids)):
            contacts = {i.removeprefix('boardModel.contact.') for i in ids if i.startswith('boardModel.contact.')}
            assert contacts == expected_contact_ids
            return rows
        time.sleep(1)
    raise RuntimeError('Simulator board did not become ready for ' + contact)

def capture(name, contact):
    rows = ready(contact)
    (out / (name + '-accessibility.json')).write_text(json.dumps(rows, indent=2) + '\n')
    time.sleep(0.8)
    run('xcrun', 'simctl', 'io', uid, 'screenshot', out / (name + '.png'))
    print(name, flush=True)
    return rows

checks = []
selections = [('jug-left', 'jug-1-left'), ('flat-left', 'flat-sloper-2-left'),
              ('round-center', 'round-sloper-3-center'), ('shallow-edge', 'edge-11-left'),
              ('deep-pocket', 'pocket-15-center')]
for name, contact in selections:
    env = dict(os.environ, SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='metolius.simulator-3d',
               SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_DETAIL='1',
               SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_HOLD_ID=contact)
    run('xcrun', 'simctl', 'launch', '--terminate-running-process', uid, 'com.hangten.training', env=env)
    before = capture(name, contact)
    checks.append({'contactID': contact, 'image': name + '.png', 'selectionAXConfirmed': True,
                   'contactsAvailable': 30})
    if name in ('jug-left', 'flat-left', 'round-center'):
        f = next(r['frame'] for r in before if r['AXUniqueId'] == 'boardDetail.map')
        run('/opt/homebrew/bin/axe', 'swipe', '--start-x', f['x'] + f['width'] * .22,
            '--start-y', f['y'] + f['height'] * .56, '--end-x', f['x'] + f['width'] * .88,
            '--end-y', f['y'] + f['height'] * .43, '--duration', '1.0', '--udid', uid)
        after = capture(name + '-orbit', contact)
        project = lambda rows: {r['AXUniqueId']: r['frame'] for r in rows
                                if (r['AXUniqueId'] or '').startswith('boardModel.contact.')}
        assert project(before) != project(after)
        checks.append({'contactID': contact, 'image': name + '-orbit.png', 'selectionAXConfirmed': True,
                       'contactsAvailable': 30, 'actualDragOrbit': True, 'projectedContactFramesChanged': True})
assert source_hash == sha(package / 'metolius-simulator-3d.FCStd')
record = {'owner': root.name, 'date': '2026-10-01', 'phase': phase,
          'simulator': uid, 'device': 'iPhone 17 Pro', 'runtime': 'iOS26.5',
          'boardID': 'metolius.simulator-3d', 'sourceSHA256': source_hash,
          'modelSHA256': sha(package / 'assets/primary.usdz'),
          'descriptorSHA256': sha(package / 'assets/primary.model.json'),
          'builtBinarySHA256': sha(app / 'HangTen'), 'surfaceFinish': 'neutral (unchanged)',
          'checks': checks, 'commands': commands, 'humanGeometryAcceptance': 'pending revised review #8',
          'limits': 'Full-frame app captures and AX selection; representative contacts and three real drags, not an all-contact visual sweep or manufacturer accuracy certification.'}
(out / 'validation.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'captured': len(checks), 'actualOrbitsVerified': 3, 'phase': phase, 'sourceSHA256': source_hash}))
