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
args = parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
tool = Path(__file__).resolve().parent
root = REPO / '.context' / (REPO.name + '-current-' + args.label)
root.mkdir()
stage = root / 'native'; stage.mkdir()
sources = stage / 'sources'; sources.mkdir()
original = {name: baseline(name) for name in NAMES}
for name in NAMES:
    text = (REPO / 'HangTen/Models' / name).read_text()
    if name == 'RopeDynamicsSolver.swift':
        text = text.replace('private extension SIMD4', 'extension SIMD4')
        text += '\n' + (tool / 'stock_chain/CheckpointAdapter.swift').read_text()
        text += '\nextension RopeDynamicsSolver { func sweepCacheIdentity()->[[UInt64]]? {acceptedSegmentClearanceBounds?.map{$0.map(\\.bitPattern)}} }\n'
        if args.kind == 'trajectory':
            text = trace(text)
            needle = '                    return (convergenceExperiment ? 1:alpha)*max(maximum,abs(heightCorrection))'
            assert text.count(needle) == 1
            text = text.replace(needle, '                    ConvergenceTrace.corrections.append(["movement":max(maximum,abs(heightCorrection)),"appliedMovement":alpha*max(maximum,abs(heightCorrection)),"strain":maximumStrain(),"alpha":alpha,"rows":Double(rows.count),"active":Double(solved.ids.count-rows.filter{!$0.contact}.count)])\n' + needle)
            text = text.replace('        for r in state.ropes.indices {\n            guard collider.sweepChainIsClear', '        if ConvergenceTrace.corrections.count>=80 {ConvergenceTrace.capped=true}\n        for r in state.ropes.indices {\n            guard collider.sweepChainIsClear')
    if name == 'RopeBandedSystem.swift':
        text = text.replace('        try RopeBandedFactorization(size:size', '        return try RopeBandedFactorization(size:size')
    (sources / name).write_text(text)
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
(sources / 'main.swift').write_text(main)
files = sorted(sources.glob('*.swift'))
binary = stage / (REPO.name + '-current-screen')
command = ['xcrun', 'swiftc', '-O', '-D', 'DEBUG', '-whole-module-optimization', '-Xcc', '-DACCELERATE_NEW_LAPACK', '-module-cache-path', str(stage/'module-cache'), *map(str,files), '-o', str(binary)]
checkpoint = REPO / '.context/strong-owl-live-physics-solver-foundation/clav-contact-step/checkpoint.json'
prior = REPO / '.context/strong-owl-live-physics-accepted-profile/native/after-1.json'
inputs = [*files, *(REPO/'HangTen/Models'/n for n in NAMES), Path(__file__), checkpoint, prior, REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage / 'provenance.json').write_text(json.dumps({'owner':REPO.name,'baselineCommit':BASE,'arguments':vars(args),'command':command,'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
owner = OwnedCommands(REPO.name, stage)
for sig in [signal.SIGINT, signal.SIGTERM]: signal.signal(sig, owner.interrupted)
env = dict(os.environ)
env['HANGTEN_REVIEW_PHYSICAL_CONVERGENCE'] = '1' if args.kind == 'trajectory' else '0'
run_args = ['Hangboards/clavellium-training-block/assets/primary.physics.json', '.context/strong-owl-live-physics-candidate-discovery-reviewed/capture/frozen.json'] if args.kind == 'queries' else [str(stage), str(checkpoint), str(prior)]
try:
    status = owner.run('compile', ['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',env)
    if not status: status = owner.run('run',['perl','-e','alarm 1800;exec @ARGV',str(binary),*run_args],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally: owner.cleanup()
raise SystemExit(status)
