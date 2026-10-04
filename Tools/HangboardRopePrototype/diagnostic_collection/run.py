import argparse,pathlib,sys,json,hashlib,os,signal
sys.dont_write_bytecode=True
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from run_native_contact_screen import REPO,OwnedCommands
from diagnostic_collection.snapshot import solver_source,collider_source
ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);args=ap.parse_args()
assert REPO.name=='strong-owl-live-physics' and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
root=REPO/'.context'/f'{REPO.name}-diagnostic-collection-{args.label}';root.mkdir();sources=root/'sources';sources.mkdir()
prior=REPO/'.context/strong-owl-live-physics-armijo-b4c2027fc-preconditioned-stop-540/native'
audit=json.loads((REPO/'docs/source-audits/2026-10-03-live-preconditioned-stopping-screen.json').read_text())
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert audit['evidenceSHA256'][str((prior/'result.json').relative_to(REPO))]==h(prior/'result.json')
oldHashes=json.loads((prior/'provenance.json').read_text())['hashes']
for old in (prior/'sources').glob('*.swift'):
 assert oldHashes[str(old.relative_to(REPO))]==h(old)
 if old.name=='main.swift':continue
 text=old.read_text()
 if old.name=='RopeDynamicsSolver.swift':text=solver_source(text)
 if old.name=='RopeTriangleCollider.swift':text=collider_source(text)
 (sources/old.name).write_text(text)
tool=pathlib.Path(__file__).resolve().parent
(sources/'SolverCollection.swift').write_text((tool/'Trace.swift').read_text())
(sources/'main.swift').write_text((tool/'Main.swift.txt').read_text())
(root/'provenance.json').write_text(json.dumps({'owner':REPO.name,'priorResultSHA256':h(prior/'result.json'),'hashes':{str(p.relative_to(REPO)):h(p) for p in [*sources.glob('*.swift'),*tool.glob('*.*')] if p.is_file()}},indent=2))
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
status=1
try:
 status=c.run('compile',['perl','-e','alarm 180;exec @ARGV','xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(root/'module-cache'),*[str(p) for p in sorted(sources.glob('*.swift'))],'-o',str(root/(REPO.name+'-diagnostic-collection'))],root/'compile.log',dict(os.environ))
 if not status:status=c.run('run',['perl','-e','alarm 300;exec @ARGV',str(root/(REPO.name+'-diagnostic-collection')),str(root),str(prior/'result.json')],root/'run.log',dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1'))
finally:c.cleanup()
print((root/('compile.log' if not (root/'run.log').exists() else 'run.log')).read_text()[-5000:]);raise SystemExit(status)
