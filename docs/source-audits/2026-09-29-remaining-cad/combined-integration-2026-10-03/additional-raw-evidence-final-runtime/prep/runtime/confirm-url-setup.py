"""Handle one normal system URL confirmation before a separately measured run."""
from pathlib import Path
import json, os, re, signal, sys, time, traceback

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parent))
from common import ROOT, WORKSPACE, OWNER, IOS, sha, write_new, ownership, run, verify_controller

assert len(sys.argv) == 3, 'Usage: confirm-url-setup.py <authorized-release.json> <unique-setup-id>'
release_path = Path(sys.argv[1]).resolve()
assert release_path.is_relative_to(ROOT)
g = json.loads(release_path.read_text())
assert g['runtimeAuthorized'] and g['exclusiveRuntimeOwnership'] and g['owner'] == OWNER
assert g['boardID'] in ('zlagboard.evo', 'zlagboard.pro', 'nature.stone-hanger-mini')
setup_id = sys.argv[2]
assert re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', setup_id)
out = ROOT / ('runtime-url-confirmation-' + setup_id)
out.mkdir(exist_ok=False)
write_new(out / 'helper-ownership.json', dict(owner=OWNER, resourceName=OWNER+'-url-confirmation-'+setup_id,
    pid=os.getpid(), parentPID=os.getppid(), helper=str(Path(__file__).resolve()), registeredBeforeActions=True))
d = ownership()
assert d['simulatorUUID'] == g['simulatorUUID'] and d['controllerPID'] == g['controllerPID']
assert not (IOS / 'cleanup-requested').exists()
assert sha(g['sourceReferencePath']) == g['sourceReferenceSHA256']
assert sha(g['parityPath']) == g['paritySHA256']
source = json.loads(Path(g['sourceReferencePath']).read_text())
parity = json.loads(Path(g['parityPath']).read_text())
assert parity['allEqual'] and parity['sourceUnchanged'] and parity['nativePackageCount'] == 66
assert source['selectedCanonicalFileCount'] == parity['selectedCanonicalFileCount'] == 81
for x in source['files']:
    assert sha(WORKSPACE / x['path']) == x['sha256'], x['path']
for x in parity['checks']:
    assert x['equal']
    for prefix in ('built', 'installed', 'source'):
        if prefix+'Path' in x: assert sha(x[prefix+'Path']) == x[prefix+'SHA256']
app = Path(d['installedApp'])
assert app == Path(g['installedApp']) and '/Devices/'+d['simulatorUUID']+'/' in str(app)
assert sha(app / g['binaryRelativePath']) == g['binarySHA256']
write_new(out/'bound-release.json', g)
uid = d['simulatorUUID']; bundle = 'com.hangten.training'
launched = False; app_pid = None; failure = None; handled = False; workout = False
deadline = time.monotonic()+70

def interrupted(sig, frame): raise InterruptedError(sig)
signal.signal(signal.SIGINT, interrupted); signal.signal(signal.SIGTERM, interrupted)

def command(name, args, bound=15, required=True):
    assert time.monotonic() < deadline, 'Setup-only70s bound exceeded'
    write_new(out/(name+'.intent.json'), dict(owner=OWNER, resourceName=OWNER+'-url-confirmation-'+setup_id+'-'+name,
        command=['rtk','proxy',*map(str,args)], registeredBeforeAction=True))
    return run(out, name, args, min(bound, max(1, deadline-time.monotonic())), required=required)

def flat(nodes):
    result=[]
    for n in nodes:
        result.append(n);result.extend(flat(n.get('children',[])))
    return result

def ax(name):
    command(name, ['/opt/homebrew/bin/axe','describe-ui','--udid',uid])
    return json.loads((out/(name+'.stdout')).read_text())

try:
    verify_controller(d, out)
    flags={k:v for k,v in g['launchReviewFlags'].items()}
    assert flags=={'HANGTEN_REVIEW_BOARD_ID':g['boardID'],'HANGTEN_REVIEW_PLAN_ID':'research.max-hangs','HANGTEN_REVIEW_LANDSCAPE':'1'}
    environment={k:v for k,v in os.environ.items() if k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_')}
    for k in list(environment): del os.environ[k]
    os.environ.update({'SIMCTL_CHILD_'+k:v for k,v in flags.items()})
    write_new(out/'app-intent.json', dict(owner=OWNER, resourceName=OWNER+'-url-confirmation-'+setup_id+'-app',
        simulatorUUID=uid, bundle=bundle, installedApp=str(app), registeredBeforeLaunch=True))
    launched=True
    try:
        command('launch', ['xcrun','simctl','launch','--terminate-running-process',
            '--stdout='+str(out/'app.stdout'),'--stderr='+str(out/'app.stderr'),uid,bundle,'-workoutAudioCuesEnabled','NO'])
    finally:
        for k in list(os.environ):
            if k.startswith('SIMCTL_CHILD_HANGTEN_REVIEW_'):del os.environ[k]
        os.environ.update(environment)
    response=(out/'launch.stdout').read_text().strip()
    match=re.search(r':\s*(\d+)\s*$',response);assert match, 'Exact appPID registration required'
    app_pid=int(match.group(1))
    write_new(out/'app-registration.json', dict(owner=OWNER, simulatorUUID=uid, bundle=bundle,pid=app_pid))
    time.sleep(2)
    before=ax('train-setup')
    assert any(n.get('AXUniqueId')=='train.board' and n.get('AXLabel')==g['boardName'] for n in flat(before))
    command('openurl',['xcrun','simctl','openurl',uid,'hangten://plan/research.max-hangs/workout'])
    time.sleep(.5)
    alert=ax('url-confirmation-before')
    nodes=flat(alert)
    open_nodes=[n for n in nodes if n.get('AXLabel')=='Open']
    cancel_nodes=[n for n in nodes if n.get('AXLabel')=='Cancel']
    assert len(open_nodes)==1 and cancel_nodes, 'One normal system confirmation required; stop without retry'
    command('confirmation-before-screenshot',['xcrun','simctl','io',uid,'screenshot',out/'system-confirmation-before.png'])
    command('physical-open-once',['/opt/homebrew/bin/axe','tap','--label','Open','--tap-style','physical','--udid',uid])
    handled=True
    time.sleep(1)
    after=ax('workout-after-confirmation')
    workout=any(n.get('AXUniqueId')=='workout.routinePicker' for n in flat(after))
    assert workout, 'Normal workout route must be present after one Open; no further action/retry'
    command('workout-after-screenshot',['xcrun','simctl','io',uid,'screenshot',out/'workout-after-confirmation.png'])
except BaseException:
    failure=traceback.format_exc();(out/'failure.txt').write_text(failure)
finally:
    # Only exact newly launched app and common.run's registered process groups.
    cleanup=dict(scope='Exact setup app only; Simulator/DD/frontend remain root-controller owned')
    if launched:
        try:
            run(out,'terminate-exact-app',['xcrun','simctl','terminate',uid,bundle],10,required=False)
            if app_pid:
                status=run(out,'verify-exact-app-pid',['ps','-p',app_pid,'-o','pid=,comm='],5,required=False)
                cleanup['appPIDAbsent']=status==1 and not (out/'verify-exact-app-pid.stdout').read_text().strip()
            else:cleanup['appPIDAbsent']=False
        except BaseException:cleanup['error']=traceback.format_exc()
    else:cleanup['appPIDAbsent']=True
    postflight=True
    try:
        for x in source['files']: assert sha(WORKSPACE/x['path'])==x['sha256']
        for x in parity['checks']:
            for prefix in ('built','installed','source'):
                if prefix+'Path' in x: assert sha(x[prefix+'Path'])==x[prefix+'SHA256']
    except BaseException:
        postflight=False;cleanup['postflightError']=traceback.format_exc()
    cleanup['sourceAndParityUnchanged']=postflight
    cleanup['passed']=cleanup['appPIDAbsent'] and 'error' not in cleanup and postflight
    write_new(out/'cleanup.json',cleanup)
    write_new(out/'completion.json',dict(owner=OWNER,boardID=g['boardID'],simulatorUUID=uid,
        binarySHA256=g['binarySHA256'],sourceReferenceSHA256=g['sourceReferenceSHA256'],
        paritySHA256=g['paritySHA256'],setupOnly=True,measurementRun=False,
        confirmationHandledBeforeMeasurement=handled,normalWorkoutConfirmed=workout,
        physicalOpenCount=1 if handled else 0,noRetries=True,cleanupPassed=cleanup['passed'],
        passed=failure is None and handled and workout and cleanup['passed']))
if failure or not cleanup['passed']:raise SystemExit(1)
