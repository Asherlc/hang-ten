#!/usr/bin/env python3
"""Complete one-shot hinted KKT candidate, with independent current-source control."""
import argparse, hashlib, json, os, re, signal, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO, OwnedCommands
from run_live_speed_screen import NAMES
from direct_hint.snapshot import candidate as instrument

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label', required=True)
parser.add_argument('--kind',choices=['strict','pairs'],required=True)
args = parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name == 'strong-owl-live-physics'
root = REPO/'.context'/(REPO.name+'-direct-hint-candidate-'+args.label)
root.mkdir()
stage = root/'native'; stage.mkdir()
sources = stage/'sources'; sources.mkdir()
tool = Path(__file__).resolve().parent
adapter = (tool/'stock_chain/CheckpointAdapter.swift').read_text()
inputs = [REPO/'HangTen/Models'/name for name in NAMES]
for path in inputs:
    original = path.read_text()
    text = instrument(path.name, original)
    if path.name == 'RopeDynamicsSolver.swift':
        text = text.replace('private extension SIMD4', 'extension SIMD4')+'\n'+adapter
        original = re.sub(r'private extension SIMD4 where Scalar == Double \{\s*var xyz:SIMD3<Double>\{SIMD3\(x,y,z\)\}\s*\}', '', original)+'\n'+adapter
    (sources/path.name).write_text(text)
    control = re.sub(r'\bRope[A-Z]\w*', lambda m: 'Control'+m[0], original)
    (sources/('Control'+path.name)).write_text(control)
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
main = (tool/'triangle_kernel_cache/main.swift').read_text()
start=main.index('func compare(')
end=main.index('for step in 1...139',start)
main=main[:start]+r'''func difference(_ x:RopeDynamicsSolver,_ y:ControlRopeDynamicsSolver)->Double {
    var value=abs(x.state.boardHeight-y.state.boardHeight)
    for r in x.state.ropes.indices {for i in x.state.ropes[r].positions.indices {
        value=max(value,simd_distance(x.state.ropes[r].positions[i],y.state.ropes[r].positions[i]))
    }}
    return value
}
func compare(_ x:RopeDynamicsSolver,_ y:ControlRopeDynamicsSolver) throws {
    guard difference(x,y)<=1e-6,x.reviewStepCorrections==y.reviewStepCorrections,
          x.reviewStepCaps==y.reviewStepCaps,x.reviewStepRetries==y.reviewStepRetries else {
        throw RopePhysicsError.invalid("current-control difference or correction schedule changed: \(difference(x,y))")
    }
    for r in x.state.ropes.indices {
        let a=x.state.ropes[r],b=y.state.ropes[r]
        guard a.radius==b.radius,a.linearMass==b.linearMass,a.restLengths==b.restLengths,
            a.supports==b.supports,a.attachments==b.attachments,a.portals==b.portals,a.channelSegments==b.channelSegments else {
            throw RopePhysicsError.invalid("material or bindings changed")
        }
    }
}
'''+main[end:]
if args.kind=='strict':
    main=main[:main.index('for step in 1...139')]+'''
var reports:[[String:Any]]=[]
for step in 1...20 {
    HintCandidateTrace.reset()
    alarm(10)
    let frame=try candidate.step(dt:1.0/240,targetOrientation:target)
    let reference=try control.step(dt:1.0/240,targetOrientation:target)
    alarm(0)
    try compare(candidate,control)
    guard frame.metrics.geometryAccepted,reference.metrics.geometryAccepted else {throw RopePhysicsError.invalid("physical metrics")}
    reports.append(["step":step,"maximumDifferenceMeters":difference(candidate,control),
        "attempts":HintCandidateTrace.attempts,"accepted":HintCandidateTrace.accepted,"exceptions":HintCandidateTrace.exceptions,
        "corrections":candidate.reviewStepCorrections,"caps":candidate.reviewStepCaps,"retries":candidate.reviewStepRetries])
    print("strict",step,difference(candidate,control),"direct",HintCandidateTrace.accepted,"of",HintCandidateTrace.attempts);fflush(stdout)
}
let result:[String:Any]=["owner":"strong-owl-live-physics","reports":reports,"accuracyPassed":true,"adopted":false,
    "scope":"20 actual-seed propagated paired current-control steps; 1 micron pose gate, all physical checks, material identity and correction/cap/retry schedule"]
try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
print("PASS direct hinted KKT strict discriminator")
'''
else:
    main=main.replace('        let t=ProcessInfo.processInfo.systemUptime\n        _ = try x.step','        HintCandidateTrace.reset()\n        let t=ProcessInfo.processInfo.systemUptime\n        _ = try x.step')
    main=main.replace('"wholePhysicalCheckpointBitIdentity":true','"maximumDifferenceMeters":difference(x,y),"directAttempts":HintCandidateTrace.attempts,"directAccepted":HintCandidateTrace.accepted,"directExceptions":HintCandidateTrace.exceptions')
    main=main.replace('"accuracyPassed":true','"accuracyPassed":true,"freshFullKKTCandidate":true')
main=main.replace('let root=URL(fileURLWithPath:CommandLine.arguments[1])','''var redSystem=try RopeBandedSystem(size:2,bandwidth:1)
try redSystem.addSymmetric(row:0,column:0,value:1)
try redSystem.addSymmetric(row:1,column:1,value:1)
guard redSystem.hintResidual(base:[0,0],border:[],rhs:[0,0],columns:[],borderMatrix:[],borderRHS:[])==0,
      !redSystem.hintResidual(base:[0,0],border:[],rhs:[Double.nan,0],columns:[],borderMatrix:[],borderRHS:[]).isFinite,
      !redSystem.hintResidual(base:[0,0],border:[0],rhs:[0,0],columns:[[0,0]],borderMatrix:[[0]],borderRHS:[Double.nan]).isFinite else {
    throw RopePhysicsError.invalid("nonfinite residual RED/GREEN discriminator failed")
}
let root=URL(fileURLWithPath:CommandLine.arguments[1])''')
(sources/'main.swift').write_text(main)
files = sorted(sources.glob('*.swift'))
binary = stage/(REPO.name+'-direct-hint')
command = ['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK',
           '-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),tool/'direct_hint/snapshot.py',tool/'direct_hint/Trial.swift',tool/'direct_hint/Candidate.swift',tool/'triangle_kernel_cache/main.swift',
           REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,
    'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
c = OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
env = dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1')
try:
    status = c.run('compile',['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',env)
    if not status:status = c.run('run',['perl','-e','alarm 300;exec @ARGV',str(binary),str(stage)],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
