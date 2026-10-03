#!/usr/bin/env python3
"""Non-adoptable traversal-elimination ceiling, exact recomputed contacts and solver."""
import argparse,hashlib,json,os,re,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO,OwnedCommands
from run_live_speed_screen import NAMES
from leaf_replay_ceiling.snapshot import collider_source
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label',required=True)
args=parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name=='strong-owl-live-physics'
root=REPO/'.context'/(REPO.name+'-leaf-replay-'+args.label);root.mkdir()
stage=root/'native';stage.mkdir();sources=stage/'sources';sources.mkdir()
tool=Path(__file__).resolve().parent
inputs=[REPO/'HangTen/Models'/name for name in NAMES]
adapter=(tool/'stock_chain/CheckpointAdapter.swift').read_text()
for path in inputs:
    text=path.read_text()
    if path.name=='RopeBandedSystem.swift':text=text.replace('        try RopeBandedFactorization(size:size','        return try RopeBandedFactorization(size:size')
    original=text
    if path.name=='RopeTriangleCollider.swift':text=collider_source(text)
    if path.name=='RopeDynamicsSolver.swift':
        text=text.replace('private extension SIMD4','extension SIMD4')+'\n'+adapter
        original=re.sub(r'private extension SIMD4 where Scalar == Double \{\s*var xyz:SIMD3<Double>\{SIMD3\(x,y,z\)\}\s*\}', '', original)+'\n'+adapter
    (sources/path.name).write_text(text)
    control=re.sub(r'\bRope[A-Z]\w*',lambda m:'Control'+m[0],original)
    (sources/('Control'+path.name)).write_text(control)
for name in ['ExactCheckpointJSON.swift','AcceptedSolverProfile.swift']:
    (sources/name).write_bytes((tool/'native_contact'/name).read_bytes())
main=(tool/'triangle_kernel_cache/main.swift').read_text()
main=main.replace('var reports:[[String:Any]]=[]','''collider.setLeafReplayMode(1)
var recorded=candidate,recordControl=control
_ = try recorded.step(dt:1.0/240,targetOrientation:target)
_ = try recordControl.step(dt:1.0/240,targetOrientation:target)
try compare(recorded,recordControl)
collider.setLeafReplayMode(2)
var reports:[[String:Any]]=[]''')
main=main.replace('"pairedRuns":reports,','"pairedRuns":reports,"prerecordedLists":collider.leafReplaySummary,"prerecordingExcludedFromClock":true,"nonAdoptable":true,')
main=main.replace('DEBUG convergence experiment, host-only','DEBUG convergence experiment, prerecorded exact input-keyed face/mask lists; traversal ceiling ONLY; host-only')
(sources/'main.swift').write_text(main)
files=sorted(sources.glob('*.swift'));binary=stage/(REPO.name+'-leaf-replay')
command=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),*list((tool/'leaf_replay_ceiling').glob('*.*')),tool/'triangle_kernel_cache/main.swift',REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
c=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
env=dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1')
try:
    status=c.run('compile',['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',env)
    if not status:status=c.run('run',['perl','-e','alarm 300;exec @ARGV',str(binary),str(stage)],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
