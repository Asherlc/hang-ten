from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

root = Path.cwd()
scratch = root/'.context/placid-badger/metolius-contact-app-review'
out = scratch/'captures'
out.mkdir(exist_ok=True)
uid = (scratch/'simulator-ready').read_text().strip()
app = root/'.context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app'
commands = []
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args, env=None):
    cmd = ['rtk','proxy',*map(str,args)]
    commands.append(cmd)
    return subprocess.check_output(cmd,text=True,env=env,timeout=120)
def flatten(nodes):
    rows=[]
    for node in nodes:
        if node.get('AXLabel') or node.get('AXUniqueId'):
            rows.append({k:node.get(k) for k in ('type','AXLabel','AXUniqueId','AXValue','frame')})
        rows.extend(flatten(node.get('children',[])))
    return rows
def ready(contact):
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        rows=flatten(json.loads(run('/opt/homebrew/bin/axe','describe-ui','--udid',uid)))
        ids={r['AXUniqueId'] for r in rows if r['AXUniqueId']}
        assert 'boardModel.unavailable' not in ids
        if 'boardDetail.selectedHold.'+contact in ids and 'boardModel.loading' not in ids and any(
            i.startswith('boardModel.contact.') for i in ids):
            assert len({i for i in ids if i.startswith('boardModel.contact.')})==33
            return rows
        time.sleep(1)
    raise RuntimeError('Metolius Contact did not become ready')
def capture(name,contact):
    rows=ready(contact)
    (out/(name+'-accessibility.json')).write_text(json.dumps(rows,indent=2)+'\n')
    time.sleep(0.8)
    run('xcrun','simctl','io',uid,'screenshot',out/(name+'.png'))
    print(name,flush=True)
    return rows
checks=[]
for name,contact in [('pocket-left','pocket-4-left'),('center-edge','edge-17-center'),('pinch-left','pinch-left')]:
    env=dict(os.environ,SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID='metolius.contact',
             SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_DETAIL='1',SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_HOLD_ID=contact)
    run('xcrun','simctl','launch','--terminate-running-process',uid,'com.hangten.training',env=env)
    before=capture(name,contact)
    checks.append({'contactID':contact,'image':name+'.png','selectionAXConfirmed':True,'contactsAvailable':33})
    if name=='pinch-left':
        f=next(r['frame'] for r in before if r['AXUniqueId']=='boardDetail.map')
        # Camera azimuth moves left when dragging right. Start inside live map bounds.
        sx,sy=f['x']+f['width']*0.22,f['y']+f['height']*0.56
        ex,ey=f['x']+f['width']*0.88,sy-f['height']*0.10
        run('/opt/homebrew/bin/axe','swipe','--start-x',sx,'--start-y',sy,
            '--end-x',ex,'--end-y',ey,'--duration','1.0','--udid',uid)
        after=capture('pinch-left-orbit',contact)
        project=lambda rows:{r['AXUniqueId']:r['frame'] for r in rows
                             if (r['AXUniqueId'] or '').startswith('boardModel.contact.')}
        assert project(before)!=project(after),'Actual app orbit did not change the view'
        checks.append({'contactID':contact,'image':'pinch-left-orbit.png','selectionAXConfirmed':True,
                       'contactsAvailable':33,'actualDragOrbit':True,'projectedContactFramesChanged':True})
package=root/'Hangboards/metolius-contact'
record={'owner':root.name,'date':'2026-09-30','simulator':uid,'device':'iPhone 17 Pro','runtime':'iOS26.5',
        'boardID':'metolius.contact','sourceSHA256':sha(package/'metolius-contact.FCStd'),
        'modelSHA256':sha(package/'assets/primary.usdz'),'descriptorSHA256':sha(package/'assets/primary.model.json'),
        'builtBinarySHA256':sha(app/'HangTen'),'packageChanged':False,'surfaceFinish':'neutral (unchanged)',
        'checks':checks,'commands':commands,'humanGeometryAcceptance':'pending human review#7',
        'limits':'Fresh full-frame app captures and AX selection; representative contacts and one real drag, not an all-contact visual sweep or factory geometry certification.'}
(out/'validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'captured':len(checks),'actualOrbitVerified':True,'sourceSHA256':record['sourceSHA256']}))
