import pathlib,sys,argparse,json,hashlib,os,signal
sys.dont_write_bytecode=True
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from run_native_contact_screen import REPO,OwnedCommands
from stationary_residual.snapshot import solver_source
from diagnostic_collection.snapshot import solver_source as diagnostic_solver
ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument('--checkpoint',type=int,choices=[3,140]);mode.add_argument('--trajectory',action='store_true');mode.add_argument('--loaded-start',action='store_true');mode.add_argument('--loaded-trajectory',action='store_true');args=ap.parse_args()
assert REPO.name=='strong-owl-live-physics' and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
root=REPO/'.context'/f'{REPO.name}-stationary-residual-{args.label}';root.mkdir();sources=root/'sources';sources.mkdir()
prior=REPO/'.context/strong-owl-live-physics-armijo-b4c2027fc-preconditioned-stop-540/native';tool=pathlib.Path(__file__).resolve().parent
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes=json.loads((prior/'provenance.json').read_text())['hashes'];audit=json.loads((REPO/'docs/source-audits/2026-10-03-live-preconditioned-stopping-screen.json').read_text())
assert audit['evidenceSHA256'][str((prior/'result.json').relative_to(REPO))]==h(prior/'result.json')
for p in (prior/'sources').glob('*.swift'):
 assert hashes[str(p.relative_to(REPO))]==h(p)
 if p.name=='main.swift':continue
 s=p.read_text()
 if p.name=='RopeDynamicsSolver.swift':s=solver_source(diagnostic_solver(s))
 (sources/p.name).write_text(s)
(sources/'StationaryResidualTrace.swift').write_text((tool/'Trace.swift').read_text())
(sources/'SolverCollection.swift').write_text((tool.parent/'diagnostic_collection/Trace.swift').read_text())
if args.loaded_start or args.loaded_trajectory:
 if args.loaded_trajectory:
  assert json.loads((REPO/'.context/strong-owl-live-physics-stationary-residual-e09fc8a-loaded-start-3/result.json').read_text())['pass']
 (sources/'main.swift').write_text((tool/('LoadedTrajectory.swift.txt' if args.loaded_trajectory else 'LoadedStart.swift.txt')).read_text())
elif args.trajectory:
 for checkpoint in [3,140]:
  evidence=REPO/'.context'/f'{REPO.name}-stationary-residual-e540f8ff4-{checkpoint}'/'result.json'
  assert json.loads(evidence.read_text())['pass']
 text=(prior/'sources/main.swift').read_text()
 from diagnostic_collection.snapshot import once
 text=once(text,'candidate.preconditionedResidualExperiment=true','candidate.preconditionedResidualExperiment=true;candidate.stationaryResidualExperiment=true')
 text=once(text,'"trace":measured.1,"difference":difference(control,candidate),"settled":measured.2.settled]',
    '"stationaryAccepted":candidate.reviewStationaryStepAccepted,"trace":measured.1,"difference":difference(control,candidate),"settled":measured.2.settled]')
 (sources/'main.swift').write_text(text)
else:(sources/'main.swift').write_text((tool/'Checkpoint.swift.txt').read_text())
command=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(root/'module-cache'),*[str(p) for p in sorted(sources.glob('*.swift'))],'-o',str(root/(REPO.name+'-stationary-residual'))]
(root/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,'priorResultSHA256':h(prior/'result.json'),'hashes':{str(p.relative_to(REPO)):h(p) for p in [*sources.glob('*.swift'),*tool.glob('*.*'),*list((tool.parent/'diagnostic_collection').glob('*.*'))] if p.is_file()}},indent=2))
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
 status=c.run('compile',['perl','-e','alarm 180;exec @ARGV',*command],root/'compile.log',dict(os.environ))
 if not status:status=c.run('run',['perl','-e','alarm 600;exec @ARGV' if args.trajectory or args.loaded_trajectory else 'alarm 90;exec @ARGV',str(root/(REPO.name+'-stationary-residual')),str(root),*([str(REPO/'.context/strong-owl-live-physics-current-diagnostic-trajectory/native/result.json'),'--candidate-hz','240'] if args.trajectory else (["--loaded-trajectory"] if args.loaded_trajectory else []) if args.loaded_start or args.loaded_trajectory else [str(args.checkpoint)])],root/'run.log',dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1'))
finally:c.cleanup()
print((root/('run.log' if (root/'run.log').exists() else 'compile.log')).read_text()[-6000:]);raise SystemExit(status)
