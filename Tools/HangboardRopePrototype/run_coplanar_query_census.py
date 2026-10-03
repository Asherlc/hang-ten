#!/usr/bin/env python3
"""Read-only exact-plane workload census; no contact replacement or speed claim."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO, OwnedCommands
from run_live_speed_screen import NAMES


def exact_planes(mesh):
    ratios = [[float(x).as_integer_ratio() for x in p] for p in mesh['vertices']]
    denominator = max(d for p in ratios for _, d in p)
    vertices = [[n * (denominator // d) for n, d in p] for p in ratios]
    groups, ids = {}, []
    for face in mesh['triangles']:
        a, b, c = [vertices[i] for i in face]
        u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
        n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        assert any(n), 'degenerate triangle'
        plane = [*n, sum(n[i]*a[i] for i in range(3))]
        divisor = math.gcd(*plane)
        plane = [x // divisor for x in plane]
        if next(x for x in plane[:3] if x) < 0:
            plane = [-x for x in plane]
        key = tuple(plane)
        if key not in groups:
            groups[key] = len(groups)
        ids.append(groups[key])
    return ids, denominator


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--label', required=True)
args = p.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name == 'strong-owl-live-physics'
root = REPO / '.context' / (REPO.name+'-coplanar-query-'+args.label)
root.mkdir()
stage = root / 'native'; stage.mkdir()
sources = stage / 'sources'; sources.mkdir()
tool = Path(__file__).resolve().parent
descriptor = REPO / 'Hangboards/clavellium-training-block/assets/primary.physics.json'
ids, denominator = exact_planes(json.loads(descriptor.read_text())['collision'])
(stage/'planes.json').write_text(json.dumps({'facePlaneIDs': ids, 'denominator': str(denominator)}))
# The 50% overlap threshold is a necessary optimistic screen, fixed before execution.
# At the retained 45% triangle-cost share, even deleting half that work saves only 22.5%.
(stage/'PLAN.md').write_text('''Read-only census at fixed steps 1,6,109,140,493 of the original 240Hz trajectory.
Candidate and independent control must retain identical persisted physics checkpoints
and correction decisions at every step. Count fused candidate-face visits and unique
exact supporting planes per query; no contact arithmetic is removed. If optimistic
plane reuse removes <50% of face visits at step140, close this geometry line before
replacement implementation. Passing only permits further feasibility analysis, not
product adoption or a real-time claim. Masks, fractions, internal edges, disconnected
regions and floating arithmetic can still prevent this optimistic reuse.
''')
adapter = (tool/'stock_chain/CheckpointAdapter.swift').read_text()
inputs = [REPO/'HangTen/Models'/name for name in NAMES]
for path in inputs:
    original = path.read_text()
    if path.name == 'RopeBandedSystem.swift':
        original = original.replace('        try RopeBandedFactorization(size:size', '        return try RopeBandedFactorization(size:size')
    candidate = original
    if path.name == 'RopeTriangleCollider.swift':
        needle = '    private let tree: [Node]\n'
        assert candidate.count(needle) == 1
        candidate = candidate.replace(needle, needle+'    let planeCensus = RopePlaneCensus()\n')
        needle = '        var minimum=Double.infinity\n        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {'
        assert candidate.count(needle) == 1
        candidate = candidate.replace(needle, '        planeCensus.record(faces, start, end)\n'+needle)
    if path.name == 'RopeDynamicsSolver.swift':
        candidate = candidate.replace('private extension SIMD4', 'extension SIMD4')+'\n'+adapter
        original = re.sub(r'private extension SIMD4 where Scalar == Double \{\s*var xyz:SIMD3<Double>\{SIMD3\(x,y,z\)\}\s*\}', '', original)+'\n'+adapter
    (sources/path.name).write_text(candidate)
    (sources/('Control'+path.name)).write_text(re.sub(r'\bRope[A-Z]\w*', lambda m:'Control'+m[0], original))
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
(sources/'Census.swift').write_text('''import Foundation
import simd
final class RopePlaneCensus: @unchecked Sendable {
    static let planes: [Int] = '''+json.dumps(ids)+'''
    private let lock = NSLock()
    var enabled = false // Driver changes only outside joined query workers.
    private var queries = 0, visits = 0, unique = 0, repeatedQueries = 0
    private var examples: [[String:Any]] = []
    func record(_ faces:[(Int,Int)], _ a:SIMD3<Double>, _ b:SIMD3<Double>) {
        guard enabled else {return}
        let planes = Set(faces.map {Self.planes[$0.0]})
        lock.lock(); defer {lock.unlock()}
        queries += 1; visits += faces.count; unique += planes.count
        if faces.count > planes.count {repeatedQueries += 1}
        if faces.count >= 20 && examples.count < 20 {
            examples.append(["start":[a.x,a.y,a.z],"end":[b.x,b.y,b.z],
                "faces":faces.map {[$0.0,$0.1]},"uniquePlanes":planes.count])
        }
    }
    func reset() {queries=0; visits=0; unique=0; repeatedQueries=0; examples=[]}
    var summary:[String:Any] {
        lock.lock(); defer {lock.unlock()}
        return ["queries":queries,"faceVisits":visits,"uniquePlaneVisits":unique,
            "repeatedQueries":repeatedQueries,"optimisticRemovedFraction":visits>0 ? Double(visits-unique)/Double(visits):0,
            "examples":examples]
    }
}
extension RopeTriangleCollider {
    func setPlaneCensus(_ enabled:Bool) {planeCensus.reset();planeCensus.enabled=enabled}
    var planeCensusSummary:[String:Any] {planeCensus.summary}
}
''')
main = (tool/'triangle_kernel_cache/main.swift').read_text()
main = main[:main.index('for step in 1...139')]+'''
let checkpoints: Set<Int> = [1,6,109,140,493]
var reports:[[String:Any]]=[]
for step in 1...493 {
    collider.setPlaneCensus(checkpoints.contains(step))
    alarm(10)
    _ = try candidate.step(dt:1.0/240,targetOrientation:step<=240 ? target:upright)
    _ = try control.step(dt:1.0/240,targetOrientation:step<=240 ? target:upright)
    alarm(0)
    try compare(candidate,control)
    if checkpoints.contains(step) {
        reports.append(["step":step,"corrections":candidate.reviewStepCorrections,
            "caps":candidate.reviewStepCaps,"retries":candidate.reviewStepRetries,
            "census":collider.planeCensusSummary,"persistedPhysicsCheckpointBitIdentity":true])
    }
    if step%50==0 {print("prefix",step,"matched");fflush(stdout)}
}
let fixed = reports.first {$0["step"] as! Int == 140}!["census"] as! [String:Any]
let fraction = fixed["optimisticRemovedFraction"] as! Double
let result:[String:Any] = ["owner":"strong-owl-live-physics","adopted":false,
    "scope":"instrumentation-only exact supporting-plane query census; no arithmetic skipped; timings invalid",
    "steps":reports,"identicalSteps":493,"fixedNecessaryRemovedFraction":0.5,
    "necessaryScreenPassed":fraction>=0.5]
try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
print("optimistic plane reuse fraction",fraction)
'''
(sources/'main.swift').write_text(main)
files = sorted(sources.glob('*.swift'))
binary = stage/(REPO.name+'-coplanar-query')
cmd = ['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files, Path(__file__), descriptor, tool/'triangle_kernel_cache/main.swift', tool/'stock_chain/CheckpointAdapter.swift', stage/'PLAN.md', stage/'planes.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':cmd,'hashes':{str(x.relative_to(REPO)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}},indent=2))
c = OwnedCommands(REPO.name, stage)
for sig in (signal.SIGINT, signal.SIGTERM):signal.signal(sig, c.interrupted)
env = dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1')
try:
    status = c.run('compile',['perl','-e','alarm 150;exec @ARGV',*cmd],stage/'compile.log',env)
    if not status:status=c.run('run',['perl','-e','alarm 300;exec @ARGV',str(binary),str(stage)],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
