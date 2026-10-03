#!/usr/bin/env python3
"""Verify current app solver sources against pinned accepted sources, in owned native processes."""
import argparse, hashlib, json, os, signal, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native_contact_screen import OwnedCommands, REPO
from run_live_speed_screen import NAMES, BASE, baseline, trace

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label', required=True)
parser.add_argument('--kind', choices=['queries', 'strict', 'trajectory'], required=True)
parser.add_argument('--cached-kernels', action='store_true', help='isolated immutable triangle edge/parity cache')
parser.add_argument('--residual-stop', action='store_true', help='isolated post-step active-KKT residual stopping estimator')
parser.add_argument('--edge-tuples',action='store_true',help='remove measured per-face edge tuple heap array')
parser.add_argument('--four-triangle-kernels', action='store_true', help='isolated four-lane Double triangle kernels')
args = parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
tool = Path(__file__).resolve().parent
root = REPO / '.context' / (REPO.name + '-current-' + args.label)
root.mkdir()
stage = root / 'native'; stage.mkdir()
sources = stage / 'sources'; sources.mkdir()
original = {name: baseline(name) for name in NAMES}
assert sum([args.cached_kernels,args.residual_stop,args.four_triangle_kernels,args.edge_tuples])<=1
for name in NAMES:
    text = (REPO / 'HangTen/Models' / name).read_text()
    current_control = text
    if name=='RopeTriangleCollider.swift' and args.edge_tuples:
        from edge_tuple.snapshot import collider_source as edge_source
        text=edge_source(text)
    if name=='RopeTriangleCollider.swift' and args.four_triangle_kernels:
        from four_triangle_kernel.snapshot import collider_source as four_source
        text=four_source(text)
    if args.residual_stop:
        from residual_stop.snapshot import collider_source as residual_collider, contact_source, solver_source
        if name == 'RopeTriangleCollider.swift': text = residual_collider(text)
        if name == 'RopeContactSystem.swift': text = contact_source(text)
        if name == 'RopeDynamicsSolver.swift': text = solver_source(text)
    if name == 'RopeTriangleCollider.swift' and args.cached_kernels:
        from triangle_kernel_cache.snapshot import collider_source
        text = collider_source(text)
    if name == 'RopeDynamicsSolver.swift':
        text = text.replace('private extension SIMD4', 'extension SIMD4')
        text += '\n' + (tool / 'stock_chain/CheckpointAdapter.swift').read_text()
        text += '\nextension RopeDynamicsSolver { func sweepCacheIdentity()->[[UInt64]]? {acceptedSegmentClearanceBounds?.map{$0.map(\\.bitPattern)}} }\n'
        if args.kind == 'trajectory':
            text = trace(text)
            needle = '                    return (convergenceExperiment ? 1:alpha)*max(maximum,abs(heightCorrection))'
            assert text.count(needle) == 1
            text = text.replace(needle, '                    ConvergenceTrace.corrections.append(["movement":max(maximum,abs(heightCorrection)),"appliedMovement":alpha*max(maximum,abs(heightCorrection)),"strain":maximumStrain(),"alpha":alpha,"rows":Double(rows.count),"active":Double(solved.ids.count-rows.filter{!$0.contact}.count)])\n' + needle)
            if args.residual_stop:
                needle='if maximumStrain()<0.0002 && estimate<limit {ResidualStopTrace.stops += 1;return estimate}'
                assert text.count(needle)==1
                text=text.replace(needle,'if maximumStrain()<0.0002 && estimate<limit {ResidualStopTrace.stops += 1;ConvergenceTrace.corrections.append(["movement":estimate,"fullQP":max(maximum,abs(heightCorrection)),"strain":maximumStrain(),"alpha":alpha,"rows":Double(rows.count),"active":Double(solved.ids.count-rows.filter{!$0.contact}.count)]);return estimate}')
            text = text.replace('        for r in state.ropes.indices {\n            guard collider.sweepChainIsClear', '        if ConvergenceTrace.corrections.count>=80 {ConvergenceTrace.capped=true}\n        for r in state.ropes.indices {\n            guard collider.sweepChainIsClear')
    if name == 'RopeBandedSystem.swift':
        text = text.replace('        try RopeBandedFactorization(size:size', '        return try RopeBandedFactorization(size:size')
    (sources / name).write_text(text)
    if args.residual_stop and args.kind=='trajectory':
        import re
        if name=='RopeDynamicsSolver.swift':
            current_control=re.sub(r'private extension SIMD4 where Scalar == Double \{\s*var xyz:SIMD3<Double>\{SIMD3\(x,y,z\)\}\s*\}', '', current_control)
            current_control+='\n'+(tool/'stock_chain/CheckpointAdapter.swift').read_text()
        current_control=re.sub(r'\bRope[A-Z]\w*',lambda m:'Control'+m[0],current_control)
        (sources/('Control'+name)).write_text(current_control)
cold = original['RopeDynamicsSolver.swift'].split('enum RopeMotionSweep {')[0]
cold += '\n' + (tool / 'stock_chain/CheckpointAdapter.swift').read_text()
if args.kind == 'trajectory': cold = trace(cold)
(sources / 'ColdRopeDynamicsSolver.swift').write_text('import Foundation\n' + cold.replace('RopeDynamicsSolver', 'ColdRopeDynamicsSolver'))
for name in ['ExactCheckpointJSON.swift', 'AcceptedSolverProfile.swift']:
    (sources / name).write_bytes((tool / 'native_contact' / name).read_bytes())
if args.kind == 'queries':
    reference = original['RopeTriangleCollider.swift']
    reference = reference[reference.index('/// Exact triangle queries'):].replace('struct RopeTriangleCollider:', 'struct ReferenceTriangleCollider:')
    reference = reference.replace('    private func contains(', '    func queryParity(_ p:SIMD3<Double>)->Bool {contains(p)}\n    private func contains(')
    (sources / 'ReferenceTriangleCollider.swift').write_text('import simd\n' + reference)
    main = (tool / 'parallel_queries/query_identity.swift').read_text()
    main += '\n' + (tool / 'clearance_receipts/query_check.swift').read_text()
    main += '\n' + (tool / 'fused_sweep/query_check.swift').read_text()
elif args.kind == 'strict':
    main = (tool / 'clearance_receipts/main.swift').read_text()
else:
    main = (tool / 'physical_convergence/demo.swift').read_text()
    main = main.replace('let trace=ConvergenceTrace.result(),retries=ConvergenceTrace.retries', 'var trace=ConvergenceTrace.result();let retries=solver.reviewStepRetries\n  trace["retries"]=retries;trace["capped"]=solver.reviewStepCaps>0;trace["correctionCount"]=solver.reviewStepCorrections')
    main = main.replace('let capped=ConvergenceTrace.capped', 'let capped=solver.reviewStepCaps>0')
    (sources / 'ConvergenceTrace.swift').write_bytes((tool / 'physical_convergence/Trace.swift').read_bytes())
    if args.residual_stop:
        main=main.replace('let initial=solver.state','''let controlInput=try ControlRopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let controlCollider=try ControlRopeTriangleCollider(input:controlInput)
let controlSeed=try ControlRopeThreadedSeed.make(input:controlInput,profileID:profile.id,orientation:upright,collider:controlCollider)
var trajectoryControl=try ControlRopeDynamicsSolver.prepareDisplay(input:controlInput,state:controlSeed,collider:controlCollider).solver
guard try JSONSerialization.data(withJSONObject:solver.foundationCheckpoint(),options:[.sortedKeys])==JSONSerialization.data(withJSONObject:trajectoryControl.foundationCheckpoint(),options:[.sortedKeys]) else {throw RopePhysicsError.invalid("Initial states differ")}
let initial=solver.state''')
        needle='  ConvergenceTrace.reset(threshold:0.00005);alarm(10)'
        assert main.count(needle)==1
        main=main.replace(needle,'''  alarm(10)
  let controlStart=ProcessInfo.processInfo.systemUptime
  let controlFrame=try trajectoryControl.step(dt:1.0/240,targetOrientation:target)
  let controlSeconds=ProcessInfo.processInfo.systemUptime-controlStart
  alarm(0)
  ResidualStopTrace.eligible=0;ResidualStopTrace.stops=0
'''+needle)
        needle='  if let reference {\n   var difference='
        assert main.count(needle)==1
        main=main.replace(needle,'''  var propagatedDifference=abs(solver.state.boardHeight-trajectoryControl.state.boardHeight)
  for r in solver.state.ropes.indices {for i in solver.state.ropes[r].positions.indices {
   propagatedDifference=max(propagatedDifference,simd_distance(solver.state.ropes[r].positions[i],trajectoryControl.state.ropes[r].positions[i]))
  }}
  report["controlSeconds"]=controlSeconds;report["controlCorrections"]=trajectoryControl.reviewStepCorrections
  report["propagatedDifferenceMeters"]=propagatedDifference
  report["residualEligible"]=ResidualStopTrace.eligible;report["residualStops"]=ResidualStopTrace.stops
  if propagatedDifference>0.00005 || solver.reviewStepCaps>trajectoryControl.reviewStepCaps || solver.reviewStepRetries>trajectoryControl.reviewStepRetries || !controlFrame.metrics.geometryAccepted {
   reports.append(report);throw RopePhysicsError.invalid("propagated difference or new cap/retry at \\(step): \\(propagatedDifference)")
  }
'''+needle)
        main=main.replace('"strainStop":0.0002,','"strainStop":0.0002,"postStepResidualEstimator":true,"poseGateMeters":0.00005,')
if args.residual_stop:
    main='import Foundation\nimport simd\n'+(tool/'residual_stop/Fixtures.swift').read_text()+'\n'+main
(sources / 'main.swift').write_text(main)
files = sorted(sources.glob('*.swift'))
binary = stage / (REPO.name + '-current-screen')
command = ['xcrun', 'swiftc', '-O', '-D', 'DEBUG', '-whole-module-optimization', '-Xcc', '-DACCELERATE_NEW_LAPACK', '-module-cache-path', str(stage/'module-cache'), *map(str,files), '-o', str(binary)]
checkpoint = REPO / '.context/strong-owl-live-physics-solver-foundation/clav-contact-step/checkpoint.json'
prior = REPO / '.context/strong-owl-live-physics-accepted-profile/native/after-1.json'
inputs = [*files, *(REPO/'HangTen/Models'/n for n in NAMES), Path(__file__), checkpoint, prior, REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
if args.residual_stop: inputs.extend(p for p in (tool/'residual_stop').glob('*.*') if p.is_file())
if args.edge_tuples: inputs.extend(p for p in (tool/'edge_tuple').glob('*.*') if p.is_file())
if args.four_triangle_kernels: inputs.extend(p for p in (tool/'four_triangle_kernel').glob('*.*') if p.is_file())
(stage / 'provenance.json').write_text(json.dumps({'owner':REPO.name,'baselineCommit':BASE,'arguments':vars(args),'command':command,'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
owner = OwnedCommands(REPO.name, stage)
for sig in [signal.SIGINT, signal.SIGTERM]: signal.signal(sig, owner.interrupted)
env = dict(os.environ)
env["HANGTEN_REVIEW_RESIDUAL_STOP"]="1" if args.residual_stop and args.kind=="trajectory" else "0"
env['HANGTEN_REVIEW_PHYSICAL_CONVERGENCE'] = '1' if args.kind == 'trajectory' else '0'
run_args = ['Hangboards/clavellium-training-block/assets/primary.physics.json', '.context/strong-owl-live-physics-candidate-discovery-reviewed/capture/frozen.json'] if args.kind == 'queries' else [str(stage), str(checkpoint), str(prior)]
try:
    status = owner.run('compile', ['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',env)
    if not status: status = owner.run('run',['perl','-e','alarm 1800;exec @ARGV',str(binary),*run_args],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally: owner.cleanup()
raise SystemExit(status)
