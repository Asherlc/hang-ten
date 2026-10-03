#!/usr/bin/env python3
"""Authorized native contact-manifold fixed checkpoint. No app mutation."""
import argparse,hashlib,json,os,re,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
tool=Path(__file__).resolve().parent;sys.path.insert(0,str(tool))
from run_native_contact_screen import REPO,OwnedCommands
from run_live_speed_screen import NAMES
from contact_bundle.snapshot import solver_source
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True);args=p.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name=='strong-owl-live-physics'
root=REPO/'.context'/(REPO.name+'-contact-bundle-'+args.label);root.mkdir()
stage=root/'native';stage.mkdir();sources=stage/'sources';sources.mkdir()
adapter=(tool/'stock_chain/CheckpointAdapter.swift').read_text()+'\n'+(tool/'contact_bundle/CheckpointExtras.swift').read_text()
inputs=[REPO/'HangTen/Models'/name for name in NAMES]
for path in inputs:
    original=path.read_text();text=solver_source(original) if path.name=='RopeDynamicsSolver.swift' else original
    if path.name=='RopeTriangleCollider.swift':text+='\n'+(tool/'contact_bundle/Bundle.swift').read_text()+'\n'+(tool/'contact_bundle/FeatureBatch.swift').read_text()
    if path.name=='RopeDynamicsSolver.swift':
        text=text.replace('private extension SIMD4','extension SIMD4')+'\n'+adapter
        # Only the candidate dynamics differ. Keep exact common mesh/chain/QP
        # helpers once, rather than compiling three duplicate physics stacks.
        original=original.split('enum RopeMotionSweep {')[0]+original[original.index('private struct RopeConfigurationEvaluation:Sendable {'):]+'\n'+adapter
        original=original.replace('RopeDynamicsSolver','ControlRopeDynamicsSolver').replace('RopeConfigurationEvaluation','ControlRopeConfigurationEvaluation')
        (sources/'ControlRopeDynamicsSolver.swift').write_text(original)
    (sources/path.name).write_text(text)
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
main=(tool/'contact_bundle/CheckpointMain.swift').read_text()
main=re.sub(r'\b(?:Control|Strict)Rope[A-Z]\w*',lambda m:'ControlRopeDynamicsSolver' if m[0].endswith('RopeDynamicsSolver') else re.sub(r'^(?:Control|Strict)','',m[0]),main)
(sources/'main.swift').write_text(main)
files=sorted(sources.glob('*.swift'));binary=stage/(REPO.name+'-contact-bundle-checkpoint')
cmd=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),tool/'stock_chain/CheckpointAdapter.swift',tool/'native_contact/ExactCheckpointJSON.swift',REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
inputs += list((tool/'contact_bundle').glob('*.swift'))+[tool/'contact_bundle/snapshot.py']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':cmd,'hashes':{str(x.relative_to(REPO)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}},indent=2))
c=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
env=dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1')
try:
    status=c.run('compile',['perl','-e','alarm 150;exec @ARGV',*cmd],stage/'compile.log',env)
    if not status:status=c.run('run',['perl','-e','alarm 300;exec @ARGV',str(binary),str(stage)],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
