#!/usr/bin/env python3
"""One fixed stricter-line-search screen, with original physical gates."""
import argparse,hashlib,json,os,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_native_contact_screen import OwnedCommands,REPO
from run_live_speed_screen import NAMES
from armijo.snapshot import solver_source
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert Path(os.environ.get('PASEO_WORKTREE_PATH',REPO)).resolve()==REPO and REPO.name=='strong-owl-live-physics'
tool=Path(__file__).resolve().parent
root=REPO/'.context'/f'{REPO.name}-armijo-{args.label}';root.mkdir();stage=root/'native';stage.mkdir();sources=stage/'sources';sources.mkdir()
for name in NAMES:
    text=(REPO/'HangTen/Models'/name).read_text()
    if name=='RopeDynamicsSolver.swift':
        text=solver_source(text).replace('private extension SIMD4','extension SIMD4')
        text+='\n'+(tool/'stock_chain/CheckpointAdapter.swift').read_text()+'\n'+(tool/'contact_bundle/CheckpointExtras.swift').read_text()
    if name=='RopeBandedSystem.swift':text=text.replace('        try RopeBandedFactorization(size:size','        return try RopeBandedFactorization(size:size')
    (sources/name).write_text(text)
for name in ['Math.swift','Trace.swift','main.swift']:(sources/name).write_bytes((tool/'armijo'/name).read_bytes())
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
files=sorted(sources.glob('*.swift'));binary=stage/f'{REPO.name}-armijo'
command=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK',
    '-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
prior=REPO/'.context/strong-owl-live-physics-current-diagnostic-trajectory/native/result.json'
inputs=[*files,*(REPO/'HangTen/Models'/n for n in NAMES),Path(__file__),*list((tool/'armijo').glob('*.*')),
    tool/'stock_chain/CheckpointAdapter.swift',tool/'contact_bundle/CheckpointExtras.swift',prior,
    REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,
    'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
owner=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,owner.interrupted)
env=dict(os.environ);env['HANGTEN_REVIEW_PHYSICAL_CONVERGENCE']='1'
try:
    status=owner.run('compile',['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',env)
    if not status:status=owner.run('run',['perl','-e','alarm 300;exec @ARGV',str(binary),str(stage),str(prior)],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:owner.cleanup()
raise SystemExit(status)
