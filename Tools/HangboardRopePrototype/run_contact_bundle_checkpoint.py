#!/usr/bin/env python3
"""Authorized native contact-manifold fixed checkpoint. No app mutation."""
import argparse,hashlib,json,os,re,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
tool=Path(__file__).resolve().parent;sys.path.insert(0,str(tool))
from run_native_contact_screen import REPO,OwnedCommands
from run_live_speed_screen import NAMES
from contact_bundle.snapshot import solver_source
from contact_bundle.profile_snapshot import solver_profile,collider_profile,function
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True)
p.add_argument('--profile-input',type=Path,help='Instrumentation-only census from a retained checkpoint; no acceptance retiming.')
args=p.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name=='strong-owl-live-physics'
if args.profile_input:
    args.profile_input=args.profile_input.resolve()
    assert args.profile_input.is_relative_to(REPO/'.context') and args.profile_input.is_file()
root=REPO/'.context'/(REPO.name+'-contact-bundle-'+args.label);root.mkdir()
stage=root/'native';stage.mkdir();sources=stage/'sources';sources.mkdir()
adapter=(tool/'stock_chain/CheckpointAdapter.swift').read_text()+'\n'+(tool/'contact_bundle/CheckpointExtras.swift').read_text()
inputs=[REPO/'HangTen/Models'/name for name in NAMES]
for path in inputs:
    original=path.read_text();text=solver_source(original) if path.name=='RopeDynamicsSolver.swift' else original
    if path.name=='RopeTriangleCollider.swift':text+='\n'+(tool/'contact_bundle/Bundle.swift').read_text()+'\n'+(tool/'contact_bundle/FeatureBatch.swift').read_text()
    if path.name=='RopeDynamicsSolver.swift':
        if args.profile_input:text=solver_profile(text,True)
        text=text.replace('private extension SIMD4','extension SIMD4')+'\n'+adapter
        # Only the candidate dynamics differ. Keep exact common mesh/chain/QP
        # helpers once, rather than compiling three duplicate physics stacks.
        original=original.split('enum RopeMotionSweep {')[0]+original[original.index('private struct RopeConfigurationEvaluation:Sendable {'):]+'\n'+adapter
        if args.profile_input:original=solver_profile(original,False)
        original=original.replace('RopeDynamicsSolver','ControlRopeDynamicsSolver').replace('RopeConfigurationEvaluation','ControlRopeConfigurationEvaluation')
        (sources/'ControlRopeDynamicsSolver.swift').write_text(original)
    if args.profile_input:
        if path.name=='RopeTriangleCollider.swift':text=collider_profile(text)
        if path.name=='RopeSimulationMetrics.swift':text=function(text,'selfContactPairs','self-pairs')
        if path.name=='RopeCordContacts.swift':text=function(text,'between','intercord')
    (sources/path.name).write_text(text)
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
main=(tool/'contact_bundle'/('ProfileMain.swift' if args.profile_input else 'CheckpointMain.swift')).read_text()
main=re.sub(r'\b(?:Control|Strict)Rope[A-Z]\w*',lambda m:'ControlRopeDynamicsSolver' if m[0].endswith('RopeDynamicsSolver') else re.sub(r'^(?:Control|Strict)','',m[0]),main)
(sources/'main.swift').write_text(main)
if args.profile_input:
    profile=(tool/'native_contact/AcceptedSolverProfile.swift').read_text()
    needle='        let elapsed=end-frame.start\n'
    assert profile.count(needle)==1
    profile=profile.replace(needle,needle+'        if name=="wood-original" || name=="wood-bundle" {RopeBundleCensus.wood(elapsed-frame.children)}\n')
    (sources/'AcceptedSolverProfile.swift').write_text(profile+'\n'+(tool/'contact_bundle/Profile.swift').read_text())
files=sorted(sources.glob('*.swift'));binary=stage/(REPO.name+'-contact-bundle-checkpoint')
cmd=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),tool/'stock_chain/CheckpointAdapter.swift',tool/'native_contact/ExactCheckpointJSON.swift',REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
inputs += list((tool/'contact_bundle').glob('*.swift'))+[tool/'contact_bundle/snapshot.py']
if args.profile_input:inputs += [args.profile_input,tool/'contact_bundle/profile_snapshot.py',tool/'native_contact/AcceptedSolverProfile.swift']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':cmd,'hashes':{str(x.relative_to(REPO)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}},indent=2))
c=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
env=dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1')
try:
    status=c.run('compile',['perl','-e','alarm 150;exec @ARGV',*cmd],stage/'compile.log',env)
    if not status:status=c.run('run',['perl','-e','alarm 300;exec @ARGV',str(binary),str(stage),*([str(args.profile_input)] if args.profile_input else [])],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
