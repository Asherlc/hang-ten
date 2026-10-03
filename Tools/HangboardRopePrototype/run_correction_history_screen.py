import sys,os,signal,json,hashlib,re,argparse
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'Tools/HangboardRopePrototype')
from run_native_contact_screen import OwnedCommands,REPO
parser=argparse.ArgumentParser(description="Closed correction-history full-step discriminator")
parser.add_argument('--label',required=True);args=parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('invalid label')
if Path(os.environ.get('PASEO_WORKTREE_PATH',REPO)).resolve()!=REPO or REPO.name!='strong-owl-live-physics':parser.error('wrong owner')
root=REPO/'.context'/f'{REPO.name}-correction-history-{args.label}'
if root.exists() or root.is_symlink():parser.error('fresh output required')
root.mkdir()
stage=root/'native';assert not stage.exists();stage.mkdir();snapshot=stage/'sources';snapshot.mkdir()
from correction_history.snapshot import warm_source,contact_trace
tool=REPO/'Tools/HangboardRopePrototype/correction_history'
native=REPO/'Tools/HangboardRopePrototype/native_contact'
names=['RopePhysicsDescriptor.swift','RopeTriangleCollider.swift','RopeSimulationState.swift',
 'RopeThreadedSeed.swift','RopeSimulationMetrics.swift','RopeCordContacts.swift',
 'RopeContactSystem.swift','RopeBandedSystem.swift','RopeDynamicsSolver.swift']
originals=[REPO/'HangTen/Models'/n for n in names]
for p in originals:
 text=p.read_text()
 if p.name=='RopeDynamicsSolver.swift':text=warm_source(text)
 if p.name=='RopeContactSystem.swift':text=contact_trace(text)
 if p.name=='RopeDynamicsSolver.swift':text='import Foundation\n'+text+'\n'+(REPO/'Tools/HangboardRopePrototype/stock_chain/CheckpointAdapter.swift').read_text()
 if p.name=='RopeBandedSystem.swift':
  old='        try RopeBandedFactorization(size:size'
  assert text.count(old)==1
  text=text.replace(old,'        return try RopeBandedFactorization(size:size')
 (snapshot/p.name).write_text(text)
for name in ['ExactCheckpointJSON.swift']:(snapshot/name).write_bytes((native/name).read_bytes())
(snapshot/'main.swift').write_bytes((tool/'main.swift').read_bytes())
(snapshot/'HistoryTrace.swift').write_bytes((tool/'Trace.swift').read_bytes())
files=sorted(snapshot.iterdir())
command=['xcrun','swiftc','-O','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(stage/'strong-owl-live-physics-accepted-profile')]
checkpoint=REPO/'.context/strong-owl-live-physics-solver-foundation/clav-contact-step/checkpoint.json'
prior=REPO/'.context/strong-owl-live-physics-accepted-profile/native/after-1.json'
inputs=[*files,*originals,checkpoint,prior,REPO/'Tools/HangboardRopePrototype/stock_chain/CheckpointAdapter.swift',tool/'snapshot.py',tool/'Trace.swift',tool/'main.swift',Path(__file__),REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
c=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
 status=c.run('accepted-profile-compile',['perl','-e','alarm 150; exec @ARGV',*command],stage/'compile.log',dict(os.environ))
 if not status:status=c.run('accepted-profile-run',['perl','-e','alarm 900; exec @ARGV',str(stage/'strong-owl-live-physics-accepted-profile'),str(stage),str(checkpoint),str(prior)],stage/'run.log',dict(os.environ))
 print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
