#!/usr/bin/env python3
"""Exact-input scalar geometry replay with actual complete-row upgrades."""
import argparse,hashlib,json,os,re,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO,OwnedCommands
from run_live_speed_screen import NAMES
from lazy_output_ceiling.snapshot import solver_source
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True);args=p.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name=='strong-owl-live-physics'
root=REPO/'.context'/(REPO.name+'-lazy-output-'+args.label);root.mkdir()
stage=root/'native';stage.mkdir();sources=stage/'sources';sources.mkdir()
tool=Path(__file__).resolve().parent
adapter=(tool/'stock_chain/CheckpointAdapter.swift').read_text()
adapter+='\n'+(tool/'lazy_output_ceiling/PhysicsIdentity.swift').read_text()
inputs=[REPO/'HangTen/Models'/name for name in NAMES]
for path in inputs:
    original=path.read_text();text=solver_source(original) if path.name=='RopeDynamicsSolver.swift' else original
    if path.name=='RopeDynamicsSolver.swift':
        text=text.replace('private extension SIMD4','extension SIMD4')+'\n'+adapter
        original=re.sub(r'private extension SIMD4 where Scalar == Double \{\s*var xyz:SIMD3<Double>\{SIMD3\(x,y,z\)\}\s*\}','',original)+'\n'+adapter
    (sources/path.name).write_text(text)
    (sources/('Control'+path.name)).write_text(re.sub(r'\bRope[A-Z]\w*',lambda m:'Control'+m[0],original))
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
main=(tool/'triangle_kernel_cache/main.swift').read_text()
main=main.replace('x.reviewStepCorrections==y.reviewStepCorrections,','x.lazyAdditionalPhysicsIdentity()==y.lazyAdditionalPhysicsIdentity(),\n          x.reviewStepCorrections==y.reviewStepCorrections,')
needle='var reports:[[String:Any]]=[]'
assert main.count(needle)==1
main=main.replace(needle,'''// Build the oracle from ORIGINAL full evaluation outside all measured runs.
candidate.setLazyOutputMode(1)
var recorder=candidate,recordControl=control
_ = try recorder.step(dt:1.0/240,targetOrientation:target)
_ = try recordControl.step(dt:1.0/240,targetOrientation:target)
try compare(recorder,recordControl)
candidate.setLazyOutputMode(2)
'''+needle)
main=main.replace('        let t=ProcessInfo.processInfo.systemUptime\n        _ = try x.step','        x.resetLazyOutputCounts()\n        let t=ProcessInfo.processInfo.systemUptime\n        _ = try x.step')
main=main.replace('"corrections":x.reviewStepCorrections]', '"corrections":x.reviewStepCorrections,"outputCounts":x.lazyOutputCounts]')
main=main.replace('"scope":"complete native step 140 of fixed actual upright-to-30-degree trajectory, DEBUG convergence experiment, host-only"','"oracleOnly":true,"actualScalarCandidateImplemented":false,"scope":"complete current-source step140 scalar-only oracle ceiling; actual full-row upgrades/self/intercord/QP/CCD/metrics; host-only"')
(sources/'main.swift').write_text(main)
files=sorted(sources.glob('*.swift'));binary=stage/(REPO.name+'-lazy-output')
cmd=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),tool/'lazy_output_ceiling/snapshot.py',tool/'lazy_output_ceiling/Replay.swift',tool/'lazy_output_ceiling/PhysicsIdentity.swift',tool/'triangle_kernel_cache/main.swift',REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
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
