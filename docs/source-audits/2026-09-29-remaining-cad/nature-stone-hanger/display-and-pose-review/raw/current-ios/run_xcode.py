from pathlib import Path
import json, os, signal, subprocess, sys, time, traceback
root=Path.cwd(); scratch=root/'.context/placid-badger/nature-stone-review9/vertical-groove-ios'
mode=sys.argv[1]; assert mode in ('build','tests')
uid=(scratch/'simulator-ready').read_text().strip()
assert json.loads((scratch/'ownership.json').read_text())['simulatorUUID']==uid
command=['xcodebuild','-project','HangTen.xcodeproj','-scheme','HangTen','-configuration','Debug','-destination','platform=iOS Simulator,id='+uid,'-derivedDataPath','.context/DerivedData']
result=scratch/'placid-badger-stone-vertical-groove-tests.xcresult'
if mode=='build': command+=['build-for-testing']
else:
    assert json.loads((scratch/'ios-build-command.json').read_text())['exitCode']==0
    assert not result.exists()
    command+=['-parallel-testing-enabled','NO','-collect-test-diagnostics','never','-resultBundlePath',str(result)]
    command+=['-only-testing:HangTenTests/'+name for name in ('BoardModelTests','BoardModelRealityTests','BoardPackageStoreTests','SuspendedBoardPresentationTests')]
    command+=['test-without-building']
tmp=scratch/'tmp'; tmp.mkdir(exist_ok=True)
record={'owner':root.name,'simulatorUUID':uid,'command':command,'timeoutSeconds':1200,
        'launchAttempted':False,'ownedProcessGroup':None,'cleanupVerified':False}
path=scratch/('ios-'+mode+'-command.json')
start=time.monotonic(); rc=1; proc=None; cleanup_error=None

def persist():
    path.write_text(json.dumps(record,indent=2)+'\n')

def interrupted(signum, frame):
    raise SystemExit(128+signum)

previous_handlers={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
try:
    # The cleanup scope is active before Popen and before the ownership receipt.
    with (scratch/('ios-'+mode+'.log')).open('w') as log:
        persist()
        record['launchAttempted']=True
        proc=subprocess.Popen(['rtk','proxy',*command],cwd=root,
            env=dict(os.environ,TMPDIR=str(tmp)+'/'),stdout=log,
            stderr=subprocess.STDOUT,start_new_session=True)
        record['ownedProcessGroup']=proc.pid
        persist()
        rc=proc.wait(timeout=1200)
except BaseException as exc:
    rc=124 if isinstance(exc,subprocess.TimeoutExpired) else (
        int(exc.code) if isinstance(exc,SystemExit) and isinstance(exc.code,int) else 130 if isinstance(exc,KeyboardInterrupt) else 1)
    record['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
finally:
    # A wrapper exit does not prove its descendants exited. Always address only
    # the process group created by this exact Popen, then verify its absence.
    for sig in previous_handlers: signal.signal(sig,signal.SIG_IGN)
    if proc is not None:
        try:
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            proc.wait(timeout=15)
            deadline=time.monotonic()+15
            while True:
                try: os.killpg(proc.pid,0)
                except ProcessLookupError: break
                if time.monotonic()>=deadline:
                    raise RuntimeError('Owned process group still exists after SIGKILL: '+str(proc.pid))
                time.sleep(.1)
            record['cleanupVerified']=True
            record['ownedProcessGroupAbsent']=True
        except BaseException as exc:
            cleanup_error=traceback.format_exc()
            record['cleanupFailure']={'type':type(exc).__name__,'message':str(exc),'traceback':cleanup_error}
    else:
        record['cleanupVerified']=True
        record['ownedProcessGroupAbsent']=True
        record['noProcessLaunched']=True
    if cleanup_error and rc==0: rc=1
    record.update(exitCode=rc,elapsedSeconds=time.monotonic()-start)
    try: persist()
    except BaseException:
        # Preserve failure details on stderr even when receipt storage fails.
        print(json.dumps(record,indent=2),file=sys.stderr)
        print(traceback.format_exc(),file=sys.stderr)
        if rc==0: rc=1
    for sig,handler in previous_handlers.items(): signal.signal(sig,handler)
if mode=='tests' and result.exists():
    try:
        with (scratch/'ios-summary.json').open('w') as out:
            subprocess.run(['rtk','proxy','xcrun','xcresulttool','get','test-results','summary','--path',str(result)],stdout=out,check=True,timeout=60)
    except BaseException as exc:
        record['summaryExtractionFailure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        if rc==0: rc=1
        record['exitCode']=rc
        persist()
print(json.dumps(record,indent=2)); raise SystemExit(rc)
