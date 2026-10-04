from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

root = Path.cwd()
scratch = root / '.context/placid-badger/nature-stone-review9/granite-seat-correction/ios'
phase = 'final'
out = scratch / (phase + '-captures')
out.mkdir(exist_ok=True)
uid = (scratch / 'simulator-ready').read_text().strip()
app = root / '.context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app'
package = root / 'Hangboards/nature-stone-hanger'
commands = []
command_records = []
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_hash = sha(package / 'nature-stone-hanger.FCStd')
installed = Path(subprocess.check_output(['rtk', 'proxy', 'xcrun', 'simctl', 'get_app_container',
                                         uid, 'com.hangten.training', 'app'], text=True).strip())
assert (app / 'HangTen').read_bytes() == (installed / 'HangTen').read_bytes()
assert (app / 'Hangboards/nature-stone-hanger/board.json').read_bytes() == (
    installed / 'Hangboards/nature-stone-hanger/board.json').read_bytes()
manifest = json.loads((installed / 'Hangboards/nature-stone-hanger/board.json').read_text())
expected_contact_ids = {x['id'] for x in manifest['contacts']}
assert len(expected_contact_ids) == 8

def run(*args, env=None):
    cmd = ['rtk', 'proxy', *map(str, args)]
    commands.append(cmd)
    record = {'command': cmd, 'reviewEnvironment': {k:v for k,v in (env or {}).items() if k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')}, 'startedMonotonic': time.monotonic()}
    command_records.append(record)
    receipt = out / 'command-records.json'
    receipt.write_text(json.dumps(command_records, indent=2) + '\n')
    try:
        output = subprocess.check_output(cmd, text=True, env=env, timeout=120, stderr=subprocess.STDOUT)
        record.update(exitCode=0, elapsedSeconds=time.monotonic()-record['startedMonotonic'], outputSHA256=hashlib.sha256(output.encode()).hexdigest())
        if 'describe-ui' not in cmd:
            record['output'] = output
        return output
    except BaseException as exc:
        record.update(errorType=type(exc).__name__, error=str(exc), exitCode=getattr(exc, 'returncode', None))
        if getattr(exc, 'output', None):
            record['output'] = exc.output.decode(errors='replace') if isinstance(exc.output, bytes) else exc.output
        raise
    finally:
        receipt.write_text(json.dumps(command_records, indent=2) + '\n')

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
        if ((('boardDetail.selectedHold.' + contact in ids) if contact is not None else ('train.board' in ids)) and 'boardModel.loading' not in ids
                and (contact is None or any(i.startswith('boardModel.contact.') for i in ids))):
            contacts = {i.removeprefix('boardModel.contact.') for i in ids if i.startswith('boardModel.contact.')}
            assert contact is None or (contact in contacts and contacts <= expected_contact_ids)
            return rows
        time.sleep(1)
    raise RuntimeError('Simulator board did not become ready for ' + str(contact))

def capture(name, contact):
    rows = ready(contact)
    (out / (name + '-accessibility.json')).write_text(json.dumps(rows, indent=2) + '\n')
    time.sleep(0.8)
    run('xcrun', 'simctl', 'io', uid, 'screenshot', out / (name + '.png'))
    print(name, flush=True)
    return rows

checks = []
drag_checks = []
project = lambda rows: {r['AXUniqueId']: r['frame'] for r in rows
                       if (r['AXUniqueId'] or '').startswith('boardModel.contact.')}

def grasp_drag(rows, contact, index, start, end):
    f = next(r['frame'] for r in rows if r['AXUniqueId'] == 'boardDetail.map')
    run('/opt/homebrew/bin/axe', 'swipe', '--start-x', f['x'] + f['width'] * start[0],
        '--start-y', f['y'] + f['height'] * start[1],
        '--end-x', f['x'] + f['width'] * end[0],
        '--end-y', f['y'] + f['height'] * end[1], '--duration', '1.0', '--udid', uid)
    after = ready(contact)
    assert project(rows) != project(after)
    (out / f'grasp-drag-{index}-accessibility.json').write_text(json.dumps(after, indent=2) + '\n')
    drag_checks.append({'contactID': contact, 'index': index, 'startFraction': start,
                        'endFraction': end, 'selectionAXConfirmed': True,
                        'contactsAvailable': len(project(after)), 'actualDragOrbit': True,
                        'projectedContactFramesChanged': True})
    return after

# The final manifest is authoritative for each selected contact's pose.
positions=manifest['positions']
pose_for={c:p['id'] for p in positions for c in p['contactIDs']}
assert set(pose_for)==expected_contact_ids
assert len([c for p in positions for c in p['contactIDs']])==8

def launch(contact=None, telephoto=False):
    env={k:v for k,v in os.environ.items() if not k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')}
    env['SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID']='nature.stone-hanger'
    if telephoto:
        env['SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_TELEPHOTO']='1'
    if contact is not None:
        env.update(SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_DETAIL='1',SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_HOLD_ID=contact)
    run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env)

for index,contact in enumerate(c['id'] for c in manifest['contacts']):
    launch(contact)
    name=f'{index+1:02d}-'+contact
    rows=capture(name,contact)
    checks.append({'contactID':contact,'positionID':pose_for[contact],'image':name+'.png','selectionAXConfirmed':True})
    checks[-1]['normalAppearance']='Other seven contacts unselected; whole-frame material inspection required.'

# The upright granite and inverted wooden flat positions expose the same seat
# in both use directions. Front plus fresh left and right drags show its ends.
for contact,label in (('edge-front-20mm-granite','upright-granite'),
                      ('edge-front-20mm-wood-flat','inverted-wood-flat')):
    for direction,start,end in (('left',(.23,.55),(.83,.40)),
                                ('right',(.83,.55),(.23,.40))):
        launch(contact,telephoto=True)
        name='close-'+label+'-'+direction+'-front'
        rows=capture(name,contact)
        checks.append({'contactID':contact,'positionID':pose_for[contact],'image':name+'.png','selectionAXConfirmed':True,'lens':'existing DEBUG telephoto','view':'front'})
        after=grasp_drag(rows,contact,len(drag_checks)+1,start,end)
        name='close-'+label+'-'+direction+'-oblique'
        capture(name,contact)
        checks.append({'contactID':contact,'positionID':pose_for[contact],'image':name+'.png','selectionAXConfirmed':True,'actualDragOrbit':True,'view':direction+' oblique'})
        side=grasp_drag(after,contact,len(drag_checks)+1,(start[0],.50),(end[0],.50))
        name='close-'+label+'-'+direction+'-side'
        capture(name,contact)
        checks.append({'contactID':contact,'positionID':pose_for[contact],'image':name+'.png','selectionAXConfirmed':True,'actualDragOrbit':True,'view':direction+' side oblique'})
# Same live scene: granite selected, then a wood contact selected through real UI.
granite='edge-front-20mm-granite'; wood='edge-front-20mm-wood-flat'
launch(granite,telephoto=True); capture('granite-selected-before-change',granite)
run('/opt/homebrew/bin/axe','swipe','--start-x','385','--start-y','740','--end-x','385','--end-y','390','--duration','0.6','--udid',uid)
run('/opt/homebrew/bin/axe','tap','--id','boardDetail.holdLegend.'+wood,'--tap-style','physical','--post-delay','1','--udid',uid)
ready(wood)
run('/opt/homebrew/bin/axe','swipe','--start-x','385','--start-y','320','--end-x','385','--end-y','740','--duration','0.6','--udid',uid)
restored=capture('granite-deselected-same-instance',wood)
grasp_drag(restored,wood,len(drag_checks)+1,(.23,.55),(.83,.40))
capture('granite-deselected-same-instance-orbit',wood)
checks.append({'contactID':wood,'previousContactID':granite,'positionID':pose_for[wood],'sameInstanceSelectionChange':True,'image':'granite-deselected-same-instance.png','materialRestorationVerification':'Physical whole-frame image review required; no pixel inference.'})
launch(); capture('unselected-train',None)
launch(granite,telephoto=True); capture('granite-reopened',granite)
checks.append({'contactID':granite,'image':'granite-reopened.png','relaunchReappearance':True,'sameInstanceClear':False})
for rel,expected in json.loads((scratch/'final-inputs.json').read_text())['packageSHA256'].items(): assert sha(root/rel)==expected
record={'owner':root.name,'simulator':uid,'boardID':'nature.stone-hanger','phase':'granite-seat-current-source',
    'sourceSHA256':source_hash,'modelSHA256':sha(package/'assets/primary.usdz'),
    'descriptorSHA256':sha(package/'assets/primary.model.json'),'sidecarSHA256':sha(package/'suspension.json'),
    'builtBinarySHA256':sha(app/'HangTen'),'installedProvenanceSHA256':sha(scratch/'installed-app-provenance.json'),
    'checks':checks,'actualDragChecks':drag_checks,'commands':commands,
    'fileSHA256':{p.name:sha(p) for p in sorted(out.iterdir()) if p.suffix in ('.png','.json')},
    'humanAcceptance':'pending review #9 granite-seat revision','visualInspection':'Pending physical inspection; automation confirms AX state and captures full frames.',
    'limits':['No image crop, alignment, pixel measurement or geometry inference. Inspect the granite-to-wood seam in upright granite and inverted wood-flat states from both directions. The existing telephoto hook changes the lens; whole app framing is retained.',
        'The detail view always selects a contact. Normal material observations apply to unselected contacts in each full frame and the unselected Train card, not a nonexistent per-contact clear state.',
        'No UI clear/reset control exists; focused runtime tests separately cover transient-cord removal/nonpickability and camera reset.',
        'Relaunch reappearance is not same-instance clear/reset. Workout validation, if performed, is reported separately.',
        'Canonical pose is resolved from final contact membership; not independently inferred from screenshot.']}
(out/'validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'captures':len(record['fileSHA256']),'contacts':len(expected_contact_ids),'actualDrags':len(drag_checks)}))
