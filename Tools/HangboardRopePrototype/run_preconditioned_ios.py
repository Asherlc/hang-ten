#!/usr/bin/env python3
"""Stage and record a private experimental app; product source is unchanged."""
import argparse,sys,pathlib,shutil,hashlib,json,os,signal,re,subprocess
sys.dont_write_bytecode=True
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from run_native_contact_screen import OwnedCommands,REPO
from run_live_speed_screen import NAMES
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['stage','record']);ap.add_argument('--label',required=True);a=ap.parse_args()
assert REPO.name=='strong-owl-live-physics' and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label)
root=REPO/'.context'/f'{REPO.name}-preconditioned-ios-{a.label}';workspace=root/REPO.name;logs=workspace/'.context'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if a.mode=='stage':
    root.mkdir();workspace.mkdir();logs.mkdir()
    native=REPO/'.context/strong-owl-live-physics-armijo-b4c2027fc-preconditioned-stop-540/native'
    report=json.loads((native/'result.json').read_text())
    assert report['accuracyPass'] and report['measuredSteps']==540
    audit=json.loads((REPO/'docs/source-audits/2026-10-03-live-preconditioned-stopping-screen.json').read_text())
    assert audit['evidenceSHA256'][str((native/'result.json').relative_to(REPO))]==digest(native/'result.json')
    hashes=json.loads((native/'provenance.json').read_text())['hashes']
    for p in (native/'sources').glob('*.swift'):assert hashes[str(p.relative_to(REPO))]==digest(p)
    (root/'stage-ownership.json').write_text(json.dumps({'owner':REPO.name,'parentWorkspace':str(REPO),'stagedWorkspace':str(workspace),'resourcesStarted':False},indent=2))
    shutil.copytree(REPO/'HangTen',workspace/'HangTen');shutil.copytree(REPO/'HangTen.xcodeproj',workspace/'HangTen.xcodeproj')
    project=workspace/'HangTen.xcodeproj/project.pbxproj';text=project.read_text();assert text.count('path = HangTen;')==1
    # Only the app group points to copied experimental source. Build scripts,
    # board staging and the tracked-boundary check keep the real SRCROOT.
    project.write_text(text.replace('path = HangTen;', 'path = "'+str(workspace/'HangTen')+'";'))
    for name in NAMES:shutil.copyfile(native/'sources'/name,workspace/'HangTen/Models'/name)
    helpers=[p for p in sorted((native/'sources').glob('*.swift')) if p.name not in NAMES and p.name!='main.swift']
    solver=workspace/'HangTen/Models/RopeDynamicsSolver.swift'
    with solver.open('a') as f:
        for p in helpers:f.write('\n'+p.read_text()+'\n')
    controller=workspace/'HangTen/Models/LiveRopeController.swift';text=controller.read_text()
    old='    init(solver: RopeDynamicsSolver) { self.solver = solver }';assert text.count(old)==1
    controller.write_text(text.replace(old,"""    init(solver: RopeDynamicsSolver) {
        var candidate=solver
        #if DEBUG
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_PRECONDITIONED_ROPE"] == "1" {
            candidate.woodMajorizerExperiment=true;candidate.woodResidualExperiment=true
            candidate.woodFeatureIdentityExperiment=true;candidate.preconditionedResidualExperiment=true
            ResidualStopTrace.enabled=true
        }
        #endif
        self.solver=candidate
    }"""))
    (root/'staged-source.json').write_text(json.dumps({'owner':REPO.name,'accurateNativeResultSHA256':digest(native/'result.json'),'nativeHostRealtimePass':False,'adopted':False,
        'hashes':{str(p.relative_to(workspace)):digest(p) for p in [project,*list((workspace/'HangTen/Models').glob('*.swift'))]}},indent=2))
    print('STAGED',workspace)
    raise SystemExit(0)
assert os.environ.get('HANGTEN_PRECONDITIONED_IOS_EXIT_TRAP')==REPO.name, 'Run record via run_preconditioned_ios.sh so the fresh simulator has EXIT/INT/TERM cleanup'
assert workspace.is_relative_to(REPO/'.context')
metadata=json.loads((root/'stage-ownership.json').read_text());assert metadata['owner']==REPO.name and not metadata['resourcesStarted']
metadata['resourcesStarted']=True;(root/'stage-ownership.json').write_text(json.dumps(metadata,indent=2))
for name,h in json.loads((root/'staged-source.json').read_text())['hashes'].items():assert digest(workspace/name)==h
c=OwnedCommands(REPO.name,logs)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
env=dict(os.environ,PASEO_WORKTREE_PATH=str(workspace));uuid=None;pendingRegistered=False
pending=logs/'paseo-pending-simulators';owned=logs/'paseo-owned-simulators';assert not pending.exists() and not owned.exists()
derived=logs/'DerivedData';assert not derived.exists()
def run(label,args,timeout=60,required=True):
    status=c.run(label,['perl','-e',f'alarm {timeout};exec @ARGV',*map(str,args)],logs/(label+'.log'),env)
    if status and required:
        print((logs/(label+'.log')).read_text()[-7000:],flush=True);raise RuntimeError((label,status))
    return status
try:
    run('create',['xcrun','simctl','create','Hang Ten Paseo '+REPO.name+' Review Preconditioned '+a.label,'com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro','com.apple.CoreSimulator.SimRuntime.iOS-26-3'])
    uuid=(logs/'create.log').read_text().strip();assert re.fullmatch('[A-Fa-f0-9]{8}(-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12}',uuid)
    with pending.open('a') as f:f.write(uuid+'\n');f.flush();os.fsync(f.fileno())
    pendingRegistered=True
    with owned.open('a') as f:f.write(uuid+'\n');f.flush();os.fsync(f.fileno())
    (logs/'ownership.json').write_text(json.dumps({'owner':REPO.name,'uuid':uuid,'derived':str(derived),'freshInvocation':True}))
    print('SIMULATOR CREATED',uuid,flush=True)
    run('boot',['xcrun','simctl','boot',uuid]);run('bootstatus',['xcrun','simctl','bootstatus',uuid,'-b'],240)
    print('BUILDING EXPERIMENTAL APP',flush=True)
    run('build',['xcodebuild','-project',workspace/'HangTen.xcodeproj','-scheme','HangTen','-configuration','Debug','-destination','platform=iOS Simulator,id='+uuid,
        '-derivedDataPath',derived,'SRCROOT='+str(REPO),'SWIFT_OPTIMIZATION_LEVEL=-O','SWIFT_COMPILATION_MODE=wholemodule','CODE_SIGN_IDENTITY=-','CODE_SIGNING_ALLOWED=YES','build'],900)
    app=derived/'Build/Products/Debug-iphonesimulator/HangTen.app'
    run('install',['xcrun','simctl','install',uuid,app],120)
    run('container',['xcrun','simctl','get_app_container',uuid,'com.hangten.training','app'])
    installed=pathlib.Path((logs/'container.log').read_text().strip())/'HangTen';assert digest(app/'HangTen')==digest(installed)
    (logs/'installed-binary.json').write_text(json.dumps({'owner':REPO.name,'uuid':uuid,'builtSHA256':digest(app/'HangTen'),'installedSHA256':digest(installed)}))
    capture=logs/'capture';capture.mkdir()
    # Retained SCRIPT is read as evidence/template, never its historical UUID,
    # binary or ownership manifest. This fresh recorder binds only the new UUID.
    source=(REPO/'.context/strong-owl-live-physics-ios-schedule-debt-lifecycle-fix/candidate-capture/run.py').read_text()
    source=source.replace("'HANGTEN_REVIEW_PHYSICAL_CONVERGENCE':'1'","'HANGTEN_REVIEW_PHYSICAL_CONVERGENCE':'1','HANGTEN_REVIEW_PRECONDITIONED_ROPE':'1'")
    source=source.replace('range(8)','range(12)')
    source=source.replace("c.run('launch',", "assert c.run('launch',").replace("root/'launch.log',boardenv)", "root/'launch.log',boardenv)==0")
    source=source.replace("c.run('frame-'+str(i),", "assert c.run('frame-'+str(i),").replace("root/('frame-'+str(i)+'.log'),env)", "root/('frame-'+str(i)+'.log'),env)==0")
    (capture/'run.py').write_text(source)
    print('RECORDING NORMAL-SPEED APP',flush=True)
    run('capture',['python3',capture/'run.py'],120)
    print('RECORDED',capture/(REPO.name+'-motion.mp4'),flush=True)
finally:
    c.cleanup()
    if uuid and not pendingRegistered:
        devices=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))
        matching=[x for group in devices['devices'].values() for x in group if x['udid']==uuid]
        assert len(matching)==1 and matching[0]['name'].startswith('Hang Ten Paseo '+REPO.name+' ')
        subprocess.run(['rtk','proxy','xcrun','simctl','delete',uuid],check=True)
