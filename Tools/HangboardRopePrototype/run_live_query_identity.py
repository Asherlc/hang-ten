import sys,signal,os,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fused_evaluation.snapshot import collider_source
from parallel_queries.snapshot import collider_source as parallel_collider
from run_native_contact_screen import OwnedCommands,REPO
import argparse,subprocess
parser=argparse.ArgumentParser(description="934 exact queries and large parallel batch against pinned accepted source")
parser.add_argument('--label',required=True)
parser.add_argument('--receipts',action='store_true')
a=parser.parse_args()
assert a.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label)
root=REPO/'.context'/(REPO.name+'-query-'+a.label);root.mkdir()
stage=root/'query-identity';assert not stage.exists();stage.mkdir()
source=subprocess.check_output(['rtk','proxy','git','show','886067b15:HangTen/Models/RopeTriangleCollider.swift'],cwd=REPO,text=True)
parity="    func queryParity(_ point:SIMD3<Double>)->Bool {contains(point)}\n"
source=source.replace('    private func contains(',parity+'    private func contains(')
candidate=parallel_collider(collider_source(source))
if a.receipts:
 from clearance_receipts.snapshot import collider_source as receipt_collider
 candidate=receipt_collider(candidate)
(stage/'RopeTriangleCollider.swift').write_text(candidate)
reference=source[source.index('/// Exact triangle queries'):].replace('struct RopeTriangleCollider:', 'struct ReferenceTriangleCollider:')
(stage/'ReferenceTriangleCollider.swift').write_text('import simd\n'+reference)
(stage/'RopePhysicsDescriptor.swift').write_text(subprocess.check_output(['rtk','proxy','git','show','886067b15:HangTen/Models/RopePhysicsDescriptor.swift'],cwd=REPO,text=True))
test=(REPO/'Tools/HangboardRopePrototype/parallel_queries/query_identity.swift').read_text()
if a.receipts:
 test += "\n"+(REPO/'Tools/HangboardRopePrototype/clearance_receipts/query_check.swift').read_text()
(stage/'main.swift').write_text(test)
c=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
 command=['xcrun','swiftc','-O','-whole-module-optimization','-module-cache-path',str(stage/'module-cache'),*map(str,sorted(stage.glob('*.swift'))),'-o',str(stage/'strong-owl-live-physics-query-identity')]
 status=c.run('query-identity-compile',['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',dict(os.environ))
 if not status:status=c.run('query-identity-check',[str(stage/'strong-owl-live-physics-query-identity'),'Hangboards/clavellium-training-block/assets/primary.physics.json','.context/strong-owl-live-physics-candidate-discovery-reviewed/capture/frozen.json'],stage/'run.log',dict(os.environ))
 print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
 (stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.glob('*.swift')}},indent=2))
finally:c.cleanup()
raise SystemExit(status)
