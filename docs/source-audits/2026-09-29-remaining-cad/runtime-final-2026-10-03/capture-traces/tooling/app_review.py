"""Owned, whole-frame app checks. AX confirmations are not visual acceptance."""
from pathlib import Path
import argparse
import hashlib
import fcntl
import json
import math
import os
import subprocess
import time

ROOT = Path.cwd()
LANE = Path(__file__).resolve().parent
OUT = LANE / 'app-captures'
OUT.mkdir(exist_ok=True)
# The simulator and action ledger have one owner at a time. Reject overlapping
# helpers before loading the ledger or changing the actual app.
ui_lock = (OUT / 'exclusive-ui.lock').open('a')
fcntl.flock(ui_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
INPUTS = json.loads((LANE / 'final-inputs.json').read_text())
assert all(sha(ROOT / p) == value for p, value in INPUTS['packageSHA256'].items())
UID = (LANE / 'simulator-ready').read_text().strip()
assert UID == json.loads((LANE / 'ownership.json').read_text())['simulatorUUID']
PROOF = json.loads((LANE / 'installed-app-provenance.json').read_text())
assert PROOF['simulator'] == UID and PROOF['packageSHA256'] == INPUTS['packageSHA256']
assert sha(Path(PROOF['builtApp']) / 'HangTen') == PROOF['builtBinarySHA256']
assert sha(Path(PROOF['installedApp']) / 'HangTen') == PROOF['installedBinarySHA256']
for receipt in (LANE / 'commands').glob('*.json'):
    record = json.loads(receipt.read_text())
    if 'xcodebuild' in record.get('command', []):
        assert record.get('cleanupVerified'), 'Do not interact while owned XCTest runs: ' + receipt.name

LEDGER = OUT / 'actions.json'
actions = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
state_path = OUT / 'current-launch.json'


def persist():
    LEDGER.write_text(json.dumps(actions, indent=2) + '\n')


def run(*args, env=None, timeout=40):
    command = ['rtk', 'proxy', *map(str, args)]
    record = {'command': command, 'started': time.time(), 'owner': ROOT.name,
              'simulatorUUID': UID}
    if env is not None:
        record['reviewEnvironment'] = {k: v for k, v in env.items()
                                      if k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')}
    actions.append(record)
    persist()
    try:
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=timeout)
        record.update(exitCode=result.returncode, elapsedSeconds=time.time()-record['started'],
                      outputSHA256=hashlib.sha256(result.stdout.encode()).hexdigest(),
                      stderr=result.stderr)
        if 'describe-ui' not in args:
            record['stdout'] = result.stdout
        assert result.returncode == 0, (command, result.stdout[-2000:], result.stderr[-2000:])
        return result.stdout
    except BaseException as exc:
        record['exception'] = str(exc)
        raise
    finally:
        persist()


def flatten(nodes):
    rows = []
    for node in nodes:
        if node.get('AXLabel') or node.get('AXUniqueId'):
            rows.append({k: node.get(k) for k in ('type', 'AXLabel', 'AXUniqueId', 'AXValue', 'frame')})
        rows.extend(flatten(node.get('children', [])))
    return rows


def describe():
    raw = json.loads(run('/opt/homebrew/bin/axe', 'describe-ui', '--udid', UID))
    rows = flatten(raw)
    (OUT / 'latest-accessibility.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def current():
    return json.loads(state_path.read_text())


def manifest():
    return json.loads((LANE / 'generated-manifests' / (current()['package'] + '.json')).read_text())


def diagnostic(rows):
    return next((row.get('AXValue') for row in rows
                 if row.get('AXUniqueId') == 'boardModel.renderDiagnostic'), None)


def ready(contact=None, timeout=90):
    state = current()
    if contact is None:
        contact = state.get('contactID')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = describe()
        ids = {r.get('AXUniqueId') for r in rows}
        if state.get('planID') and any(r.get('AXLabel') == 'Open in \u201cHang Ten\u201d?' for r in rows):
            run('/opt/homebrew/bin/axe', 'tap', '--label', 'Open',
                '--tap-style', 'physical', '--post-delay', '.5', '--udid', UID)
            continue
        if 'boardModel.unavailable' in ids:
            raise RuntimeError('Actual app reports model unavailable; raw AX retained')
        if 'boardModel.loading' not in ids:
            if state.get('planID'):
                if 'workout.routinePicker' in ids and 'boardModel.3d' in ids:
                    return rows
            elif contact:
                if ('boardDetail.selectedHold.' + contact in ids and
                        'boardModel.contact.' + contact in ids):
                    value = diagnostic(rows)
                    if value and all(flag in str(value) for flag in
                                     ('rootActive=true', 'cameraActive=true', 'sameScene=true', 'cameraSettled=true')):
                        return rows
            elif 'train.board' in ids:
                return rows
        time.sleep(.6)
    raise RuntimeError('Expected actual board state not reached; latest-accessibility.json retained')


def save_frame(name, rows=None, **metadata):
    path = OUT / (name + '.png')
    assert not path.exists(), 'Never overwrite actual evidence: ' + name
    rows = rows if rows is not None else ready()
    (OUT / (name + '-accessibility.json')).write_text(json.dumps(rows, indent=2) + '\n')
    time.sleep(.5)
    run('xcrun', 'simctl', 'io', UID, 'screenshot', path)
    record = {'owner': ROOT.name, 'simulatorUUID': UID, 'launch': current(),
              'image': path.name, 'imageSHA256': sha(path),
              'accessibilitySHA256': sha(OUT / (name + '-accessibility.json')),
              'binarySHA256': PROOF['installedBinarySHA256'],
              'installedProvenanceSHA256': sha(LANE / 'installed-app-provenance.json'),
              'rendererDiagnostic': diagnostic(rows),
              'visualInspection': 'Pending whole-frame inspection', **metadata}
    (OUT / (name + '-receipt.json')).write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'frame': str(path), 'rendererDiagnostic': diagnostic(rows), **metadata}), flush=True)
    return rows


def projection(rows):
    frame = next(r['frame'] for r in rows if r.get('AXUniqueId') == 'boardDetail.map')
    return {r['AXUniqueId']: [(r['frame']['x']+r['frame']['width']/2-frame['x'])/frame['width'],
                            (r['frame']['y']+r['frame']['height']/2-frame['y'])/frame['height']]
            for r in rows if str(r.get('AXUniqueId') or '').startswith('boardModel.contact.')}


parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='action', required=True)
p = sub.add_parser('launch')
p.add_argument('number', type=int)
p.add_argument('contact', nargs='?')
p.add_argument('--view', choices=['front', 'side', 'top'])
p.add_argument('--landscape', action='store_true')
p.add_argument('--telephoto', action='store_true')
p.add_argument('--plan')
p.add_argument('--step', type=int, default=9)
p.add_argument('--autostart', action='store_true')
p = sub.add_parser('capture')
p.add_argument('name')
p.add_argument('--raw', action='store_true')
p = sub.add_parser('orbit')
p.add_argument('name')
p.add_argument('--start', nargs=2, type=float, default=[.23, .55])
p.add_argument('--end', nargs=2, type=float, default=[.83, .4])
p = sub.add_parser('legend')
p.add_argument('contact')
p.add_argument('name')
p = sub.add_parser('mesh-tap')
p.add_argument('contact')
p.add_argument('name')
p.add_argument('--fraction', nargs=2, type=float, default=[.5, .5])
p = sub.add_parser('tap')
p.add_argument('name')
p.add_argument('--id')
p.add_argument('--label')
p = sub.add_parser('scroll')
p.add_argument('direction', choices=['up', 'down'])
p = sub.add_parser('dump')
args = parser.parse_args()

if args.action == 'launch':
    board = next(b for b in INPUTS['boards'] if b['number'] == args.number)
    env = {k: v for k, v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')}
    flags = {'BOARD_ID': board['boardID'], 'BOARD_DIAGNOSTICS': '1', 'MODEL_DIAGNOSTICS': '1',
             'LANDSCAPE' if args.landscape else 'PORTRAIT': '1'}
    if args.contact:
        flags.update(BOARD_DETAIL='1', BOARD_HOLD_ID=args.contact)
    if args.view:
        flags['MODEL_VIEW'] = args.view
    if args.telephoto:
        flags['BOARD_TELEPHOTO'] = '1'
    if args.plan:
        flags.update(PLAN_ID=args.plan, STEP=str(args.step))
        if args.autostart:
            flags['AUTOSTART'] = '1'
    env.update({'SIMCTL_CHILD_HANGTEN_REVIEW_'+k: v for k, v in flags.items()})
    state_path.write_text(json.dumps({**board, 'contactID': args.contact, 'planID': args.plan,
                                     'flags': flags, 'launchedAt': time.time()}, indent=2) + '\n')
    if args.contact:
        assert args.contact in {c['id'] for c in manifest()['contacts']}
    run('xcrun', 'simctl', 'launch', '--terminate-running-process', UID, 'com.hangten.training', env=env)
    if args.plan:
        run('xcrun', 'simctl', 'openurl', UID, 'hangten://plan/'+args.plan+'/workout')
    rows = ready()
    print(json.dumps({'launched': board['boardID'], 'contact': args.contact,
                      'rendererDiagnostic': diagnostic(rows)}))
elif args.action == 'capture':
    save_frame(args.name, rows=describe() if args.raw else None, rawFailureCapture=args.raw)
elif args.action == 'dump':
    rows = describe()
    print(json.dumps([r for r in rows if r.get('AXUniqueId') or r.get('type') == 'Button'], indent=2))
elif args.action == 'orbit':
    before = ready()
    frame = next(r['frame'] for r in before if r.get('AXUniqueId') == 'boardDetail.map')
    run('/opt/homebrew/bin/axe', 'swipe', '--start-x', frame['x']+frame['width']*args.start[0],
        '--start-y', frame['y']+frame['height']*args.start[1],
        '--end-x', frame['x']+frame['width']*args.end[0],
        '--end-y', frame['y']+frame['height']*args.end[1], '--duration', '1', '--udid', UID)
    after = ready()
    assert projection(before) != projection(after), 'Physical orbit did not move projected contact frames'
    save_frame(args.name, after, actualPhysicalOrbit=True,
               projectedBefore=projection(before), projectedAfter=projection(after))
elif args.action == 'mesh-tap':
    before = ready()
    contact = next(r for r in before if r.get('AXUniqueId') == 'boardModel.contact.'+args.contact)
    frame = contact['frame']
    run('/opt/homebrew/bin/axe', 'tap', '-x', frame['x']+frame['width']*args.fraction[0],
        '-y', frame['y']+frame['height']*args.fraction[1], '--tap-style', 'physical', '--post-delay', '1', '--udid', UID)
    after = describe()
    value = str(diagnostic(after))
    matched = 'pickedContact='+args.contact in value.split(';')
    if not matched:
        save_frame(args.name+'-unexpected', after, actualPhysicalMeshPick=False,
                   intendedContactID=args.contact, physicalTapFraction=args.fraction,
                   rendererDiagnosticBefore=diagnostic(before))
        raise RuntimeError('Physical tap did not pick the intended contact: '+value)
    state = current()
    state['contactID'] = args.contact
    state_path.write_text(json.dumps(state, indent=2)+'\n')
    after = ready(args.contact)
    save_frame(args.name, after, actualPhysicalMeshPick=True, pickedContactID=args.contact,
               rendererDiagnosticBefore=diagnostic(before))
elif args.action == 'legend':
    assert args.contact in {c['id'] for c in manifest()['contacts']}
    for _ in range(5):
        rows = describe()
        button = next((r for r in rows if r.get('AXUniqueId') == 'boardDetail.holdLegend.'+args.contact), None)
        if button and 130 < button['frame']['y'] < 760:
            break
        run('/opt/homebrew/bin/axe', 'swipe', '--start-x', '396', '--start-y', '740',
            '--end-x', '396', '--end-y', '350', '--duration', '.6', '--udid', UID)
    assert button, 'Legend button not exposed'
    run('/opt/homebrew/bin/axe', 'tap', '--id', 'boardDetail.holdLegend.'+args.contact,
        '--tap-style', 'physical', '--post-delay', '1', '--udid', UID)
    state = current()
    state['contactID'] = args.contact
    state_path.write_text(json.dumps(state, indent=2)+'\n')
    for _ in range(2):
        run('/opt/homebrew/bin/axe', 'swipe', '--start-x', '396', '--start-y', '320',
            '--end-x', '396', '--end-y', '740', '--duration', '.6', '--udid', UID)
    save_frame(args.name, sameSceneLegendSelection=True, contactID=args.contact)
elif args.action == 'scroll':
    start, end = (740, 350) if args.direction == 'up' else (320, 740)
    run('/opt/homebrew/bin/axe', 'swipe', '--start-x', '396', '--start-y', start,
        '--end-x', '396', '--end-y', end, '--duration', '.6', '--udid', UID)
    print('Physical scroll retained')
elif args.action == 'tap':
    assert bool(args.id) != bool(args.label)
    run('/opt/homebrew/bin/axe', 'tap', '--id' if args.id else '--label', args.id or args.label,
        '--tap-style', 'physical', '--post-delay', '.5', '--udid', UID)
    save_frame(args.name)
