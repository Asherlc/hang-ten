import pathlib,sys,argparse,json,hashlib,os,signal
sys.dont_write_bytecode=True
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from run_native_contact_screen import REPO,OwnedCommands
from retained_correction.snapshot import solver_source
ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--diagnostic',action='store_true');ap.add_argument('--physical-wood',action='store_true');a=ap.parse_args()
assert not (a.diagnostic and a.physical_wood), 'strict diagnostic and physical wood modes are separate screens'
assert REPO.name=='strong-owl-live-physics' and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label)
root=REPO/'.context'/f'{REPO.name}-retained-correction-{a.label}';root.mkdir();sources=root/'sources';sources.mkdir()
prior=REPO/'.context/strong-owl-live-physics-stationary-residual-e09fc8a-loaded-full-540';tool=pathlib.Path(__file__).resolve().parent
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((REPO/'docs/source-audits/2026-10-03-live-loaded-start-screen.json').read_text())
assert audit['evidenceSHA256'][str((prior/'result.json').relative_to(REPO))]==h(prior/'result.json')
hashes=json.loads((prior/'provenance.json').read_text())['hashes']
for p in (prior/'sources').glob('*.swift'):
 assert hashes[str(p.relative_to(REPO))]==h(p)
 if p.name=='main.swift':continue
 s=p.read_text()
 if p.name=='RopeDynamicsSolver.swift':s=solver_source(s,diagnostic=a.diagnostic,physical_wood=a.physical_wood)
 (sources/p.name).write_text(s)
main=(tool/'Main.swift.txt').read_text()
if a.physical_wood:main=main.replace('candidate.retainedCorrectionExperiment=true','candidate.retainedCorrectionExperiment=true;candidate.retainedPhysicalWoodExperiment=true')
(sources/'main.swift').write_text(main)
command=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(root/'module-cache'),*[str(p) for p in sorted(sources.glob('*.swift'))],'-o',str(root/(REPO.name+'-retained-correction'))]
(root/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,'loadedInputSHA256':h(prior/'loaded-input.json'),'hashes':{str(p.relative_to(REPO)):h(p) for p in sources.glob('*.swift')}},indent=2))
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
 status=c.run('compile',['perl','-e','alarm 180;exec @ARGV',*command],root/'compile.log',dict(os.environ))
 if not status:status=c.run('run',['perl','-e','alarm 90;exec @ARGV',str(root/(REPO.name+'-retained-correction')),str(root),str(prior/'loaded-input.json')],root/'run.log',dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1'))
finally:c.cleanup()
print((root/('run.log' if (root/'run.log').exists() else 'compile.log')).read_text()[-5000:]);raise SystemExit(status)
