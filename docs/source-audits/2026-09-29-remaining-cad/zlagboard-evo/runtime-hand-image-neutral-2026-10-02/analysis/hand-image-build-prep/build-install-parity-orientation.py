"""PREPARED ONLY. Requires root's explicit fresh gate. Uses existing lifecycle resources."""
from pathlib import Path
import argparse,hashlib,json,shlex,signal,subprocess,sys
ROOT=Path.cwd().resolve()
R=ROOT/'.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02'
PREP=R/'hand-image-build-prep'
UUID='BDCA0D77-94C2-4A97-900B-443F75C64691'
OWNER='placid-badger-cad-second-half'
CONTROLLER=96137
LIFE=R/'ios-diagnosis'
DD=LIFE/('DerivedData-'+OWNER)
APP=DD/'Build/Products/Debug-iphonesimulator/HangTen.app'
BOUND=R/'prep/bounded-command.py'
SOURCE_PATHS=['HangTen/Models/BoardModelRealityTypes.swift','HangTen/Views/BoardModelView.swift','HangTen/Views/GripHandModelView.swift','HangTen/Views/RootView.swift','HangTen/Views/TrainView.swift']
MACHO_NAMES={'__preview.dylib','HangTen','HangTen.debug.dylib','Frameworks/Sentry.framework/Sentry','Frameworks/AmplitudeCore.framework/AmplitudeCore'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
ACTIVE_HELPER=None
def interrupted(signum,_):
 if ACTIVE_HELPER is not None and ACTIVE_HELPER.poll() is None:
  ACTIVE_HELPER.send_signal(signum)
  try: ACTIVE_HELPER.wait(timeout=20)
  except subprocess.TimeoutExpired: raise RuntimeError('Bounded helper did not exit after interruption; root owns recovery, do not broad-kill')
 raise SystemExit(128+signum)
signal.signal(signal.SIGINT,interrupted)
signal.signal(signal.SIGTERM,interrupted)
def run(seconds,label,*args):
 global ACTIVE_HELPER
 # Existing reviewed helper owns its subprocess group and retains output on timeout/INT/TERM.
 ACTIVE_HELPER=subprocess.Popen(['rtk','proxy','python3',str(BOUND),str(seconds),str(OUT/(label+'.json')),*map(str,args)])
 code=ACTIVE_HELPER.wait()
 ACTIVE_HELPER=None
 if code:raise RuntimeError(f'{label} failed: {code}; see exact raw logs')
 return (OUT/(label+'.stdout')).read_text()
def source_checks():
 return [{'category':'source','path':s,'sha256':sha(ROOT/s),'expected':GATE['sourceSHA256'][s],'equal':sha(ROOT/s)==GATE['sourceSHA256'][s]} for s in SOURCE_PATHS]
def macho(app):
 magic={b'\xfe\xed\xfa\xce',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca',b'\xca\xfe\xba\xbf',b'\xbf\xba\xfe\xca'}
 found={}
 for p in app.rglob('*'):
  if p.is_file():
   with p.open('rb') as f:head=f.read(4)
   if head in magic:found[str(p.relative_to(app))]={'sha256':sha(p),'bytes':p.stat().st_size}
 return found
parser=argparse.ArgumentParser();parser.add_argument('--gate',required=True);parser.add_argument('--output',required=True);parser.add_argument('--completed-build-record',required=True);a=parser.parse_args()
GATE=json.loads(Path(a.gate).read_text());OUT=Path(a.output).resolve()
assert GATE['authorizedByParent'] is True and GATE['exclusiveBuildInstallOwnership'] is True
assert GATE['owner']==OWNER and GATE['simulator']==UUID and GATE['controllerPID']==CONTROLLER
assert set(GATE['sourceSHA256'])==set(SOURCE_PATHS)
assert OUT.is_relative_to(R) and not OUT.exists(),'Fresh workspace-owned output directory required'
assert ROOT.name==OWNER and not (LIFE/'cleanup-requested').exists()
ownership=json.loads((LIFE/'ownership.json').read_text())
assert ownership['simulator']==UUID and ownership['owner']==OWNER and Path(ownership['derivedData']).resolve()==DD
assert UUID in (ROOT/'.context/paseo-owned-simulators').read_text().splitlines()
assert DD.is_dir() and BOUND.is_file()
OUT.mkdir();write(OUT/'authorization-input.json',GATE)
try:
 controller=run(10,'controller-preflight','ps','-p',str(CONTROLLER),'-o','pid=,args=')
 controller_tokens=shlex.split(controller)
 assert controller_tokens[0]==str(CONTROLLER) and any(t in {str(R/'prep/lifecycle.zsh'),str((R/'prep/lifecycle.zsh').relative_to(ROOT))} for t in controller_tokens[1:]),'Exact cleanup controller not verified'
 devices=json.loads(run(20,'device-preflight','xcrun','simctl','list','devices',UUID,'--json'))
 matches=[d for ds in devices['devices'].values() for d in ds if d['udid']==UUID]
 assert len(matches)==1 and matches[0]['state']=='Booted' and OWNER in matches[0]['name']
 before=source_checks();write(OUT/'source-before.json',before);assert all(x['equal'] for x in before)
 for s in SOURCE_PATHS:
  q=OUT/'source'/s;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((ROOT/s).read_bytes())
 build_record=Path(a.completed_build_record).resolve()
 assert build_record==R/'evo/hand-image-orientation-build-command.json'
 assert sha(build_record)==GATE['completedBuildRecordSHA256'],'Root must authorize this exact completed build record'
 build=json.loads(build_record.read_text())
 assert build['exitStatus']==0 and not build['timedOut'] and build['interruptedBySignal'] is None
 expected=['rtk','proxy','xcodebuild','-project','HangTen.xcodeproj','-scheme','HangTen','-configuration','Debug','-destination','generic/platform=iOS Simulator','-derivedDataPath']
 assert build['command'][:len(expected)]==expected and Path(build['command'][len(expected)]).resolve()==DD and build['command'][len(expected)+1:]==['build']
 assert build['boundSeconds']==600
 write(OUT/'completed-build-reference.json',{'path':str(build_record),'sha256':sha(build_record),'buildExecutedByThisHelper':False})
 for suffix in ['.json','.stdout','.stderr']:
  origin=build_record.with_suffix(suffix);assert origin.is_file()
  with (OUT/('prior-build-command'+suffix)).open('xb') as out:out.write(origin.read_bytes())
 after=source_checks();write(OUT/'source-after-build.json',after);assert all(x['equal'] for x in after)
 built=macho(APP);write(OUT/'built-mach-o.json',built);assert set(built)==MACHO_NAMES,'Unexpected payload set; record and stop rather than ignore code'
 run(60,'install-command','xcrun','simctl','install',UUID,APP)
 installed=Path(run(20,'installed-container','xcrun','simctl','get_app_container',UUID,'com.hangten.training','app').strip()).resolve()
 assert installed.name=='HangTen.app' and f'/Devices/{UUID}/' in str(installed)
 current=macho(installed);write(OUT/'installed-mach-o.json',current);assert set(current)==MACHO_NAMES
 checks=source_checks()
 for stage,app,records in [('built',APP,built),('installed',installed,current)]:
  for name,x in records.items():checks.append({'category':stage+'MachO','path':str(app/name),'sha256':x['sha256'],'expected':built[name]['sha256'],'equal':x['sha256']==built[name]['sha256']})
 for x in json.loads((PREP/'expected-packages.json').read_text())['packages']:
  for stage,app in [('built',APP),('installed',installed)]:
   if x['name']=='board.json':paths=[app/'Hangboards'/x['slug']/'board.json']
   elif x['name']=='primary.model.json':paths=[app/'Hangboards'/x['slug']/'assets/primary.model.json']
   else:paths=list((app/'OnDemandResources').glob('*.assetpack/Hangboards/'+x['slug']+'/assets/primary.usdz'))
   assert len(paths)==1 and paths[0].is_file(),(stage,x)
   h=sha(paths[0]);checks.append({'category':'package','stage':stage,'path':str(paths[0]),'sha256':h,'expected':x['sha256'],'equal':h==x['sha256']})
 result={'allEqual':all(x['equal'] for x in checks),'count':len(checks),'builtApp':str(APP),'installedApp':str(installed),'checks':checks,'runtimeValidated':False}
 write(OUT/'parity.json',result);assert len(checks)==27 and result['allEqual']
 write(OUT/'build-install-result.json',{'status':'BUILD_INSTALL_PARITY_PASS','runtimeValidated':False,'controllerRetainsCleanupOwnership':True})
except BaseException as exc:
 write(OUT/'failure.json',{'type':type(exc).__name__,'error':str(exc),'controllerRetainsCleanupOwnership':True});raise
