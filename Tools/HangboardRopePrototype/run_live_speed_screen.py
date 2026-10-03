#!/usr/bin/env python3
"""Fresh native exact-query / convergence screens against the pinned accepted solver.

No app mutation. A label can be used once; owned process groups are always reaped.
"""
import argparse, hashlib, json, os, signal, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_native_contact_screen import OwnedCommands, REPO
from fused_evaluation.snapshot import collider_source as fused_collider,solver_source as fused_solver
from parallel_queries.snapshot import collider_source as parallel_collider,solver_source as parallel_solver
from segment_sweep_cache.snapshot import solver_source as sweep_solver,metrics_source as sweep_metrics
from clearance_receipts.snapshot import collider_source as receipt_collider,solver_source as receipt_solver,metrics_source as receipt_metrics
from working_hint.snapshot import solver_source as hint_solver
from parallel_sweep.snapshot import collider_source as sweep_collider,solver_source as parallel_sweep
BASE="886067b15"
NAMES=["RopePhysicsDescriptor.swift","RopeTriangleCollider.swift","RopeSimulationState.swift","RopeThreadedSeed.swift","RopeSimulationMetrics.swift","RopeCordContacts.swift","RopeContactSystem.swift","RopeBandedSystem.swift","RopeDynamicsSolver.swift"]
def baseline(name):
    return subprocess.check_output(["rtk","proxy","git","show",f"{BASE}:HangTen/Models/{name}"],cwd=REPO,text=True)
def trace(text):
    text=text.replace("            trial=self\n            _ = try trial.advanceBounded","            trial=self\n            ConvergenceTrace.retries += 1\n            _ = try trial.advanceBounded")
    text=text.replace("                    return alpha*max(maximum,abs(heightCorrection))",'                    ConvergenceTrace.corrections.append(["movement":alpha*max(maximum,abs(heightCorrection)),"strain":maximumStrain(),"alpha":alpha,"rows":Double(rows.count),"active":Double(solved.ids.count-rows.filter{!$0.contact}.count)])\n                    return alpha*max(maximum,abs(heightCorrection))')
    text=text.replace("        var objective=0.5*state.boardMass","        ConvergenceTrace.merits += 1\n        var objective=0.5*state.boardMass")
    text=text.replace("        for _ in 0..<16 {\n            state=before","        for _ in 0..<16 {\n            ConvergenceTrace.trials += 1\n            state=before")
    text=text.replace("        for r in state.ropes.indices {\n            let radius=state.ropes[r].radius-0.00005",'        if let last=ConvergenceTrace.corrections.last,last["movement"]!>=ConvergenceTrace.threshold || last["strain"]!>=0.0002 {ConvergenceTrace.capped=true}\n        for r in state.ropes.indices {\n            let radius=state.ropes[r].radius-0.00005')
    return text

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label",required=True)
    parser.add_argument("--kind",choices=["fused","parallel","cache","receipts","hints","convergence"],required=True)
    parser.add_argument("--parallel-sweep",action="store_true")
    parser.add_argument("--stop",choices=["scaled","undamped"],default="undamped")
    args=parser.parse_args()
    if not args.label or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.label):parser.error("label must be lowercase letters, digits, hyphens")
    root=REPO/".context"/(REPO.name+"-speed-"+args.label)
    root.mkdir() # No replacement of earlier evidence.
    stage=root/"native";stage.mkdir();snapshot=stage/"sources";snapshot.mkdir()
    parallel=args.kind!="fused";sweep=args.kind in ["cache","receipts","hints","convergence"]
    receipts=args.kind in ["receipts","convergence"];hints=args.kind in ["hints","convergence"]
    convergence=args.kind=="convergence"
    tool=Path(__file__).resolve().parent
    original={name:baseline(name) for name in NAMES}
    for name,text in original.items():
        if name=="RopeTriangleCollider.swift":
            text=fused_collider(text)
            if parallel:text=parallel_collider(text)
            if receipts:text=receipt_collider(text)
            if args.parallel_sweep:text=sweep_collider(text)
        if name=="RopeSimulationMetrics.swift" and sweep:
            text=sweep_metrics(text)
            if receipts:text=receipt_metrics(text)
        if name=="RopeDynamicsSolver.swift":
            text=fused_solver(text)
            if parallel:text=parallel_solver(text)
            if sweep:text=sweep_solver(text)
            if receipts:text=receipt_solver(text)
            if hints:text=hint_solver(text)
            if args.parallel_sweep:text=parallel_sweep(text)
            if convergence:
                text=trace(text.replace("movement<1e-8 {break}","movement<0.00005 {break}"))
                if args.stop=="undamped":
                    text=text.replace("return alpha*max(maximum,abs(heightCorrection))","return max(maximum,abs(heightCorrection))")
                    text=text.replace('"movement":alpha*max(maximum,abs(heightCorrection))','"movement":max(maximum,abs(heightCorrection)),"appliedMovement":alpha*max(maximum,abs(heightCorrection))')
                if args.parallel_sweep:
                    text=text.replace('        for r in state.ropes.indices {\n            guard collider.sweepChainIsClear','        if ConvergenceTrace.corrections.count>=80 {ConvergenceTrace.capped=true}\n        for r in state.ropes.indices {\n            guard collider.sweepChainIsClear')
            else:
                text=text.replace("        var points:[[[RopeSegmentContact]]]=[]","        EvaluationAudit.evaluations += 1\n        var points:[[[RopeSegmentContact]]]=[]")
                text=text.replace("        var objective=0.5*state.boardMass","        EvaluationAudit.merits += 1\n        var objective=0.5*state.boardMass")
                text+="\n"+(tool/"fused_evaluation/TestHooks.swift").read_text()
            text="import Foundation\n"+text+"\n"+(tool/"stock_chain/CheckpointAdapter.swift").read_text()
            text=text.replace("private extension SIMD4","extension SIMD4")
        if name=="RopeBandedSystem.swift":text=text.replace("        try RopeBandedFactorization(size:size","        return try RopeBandedFactorization(size:size")
        (snapshot/name).write_text(text)
    cold=original["RopeDynamicsSolver.swift"].split("enum RopeMotionSweep {")[0]
    cold+="\n"+(tool/"stock_chain/CheckpointAdapter.swift").read_text()
    if convergence:cold=trace(cold)
    else:
        hooks=(tool/"fused_evaluation/TestHooks.swift").read_text().split("extension RopeDynamicsSolver {")[1]
        cold+="\nextension RopeDynamicsSolver {\n"+hooks[hooks.index("    mutating func debugMerit"):]
    (snapshot/"ColdRopeDynamicsSolver.swift").write_text("import Foundation\n"+cold.replace("RopeDynamicsSolver","ColdRopeDynamicsSolver"))
    for name in ["ExactCheckpointJSON.swift","AcceptedSolverProfile.swift"]:(snapshot/name).write_bytes((tool/"native_contact"/name).read_bytes())
    test={"fused":"fused_evaluation/RepeatMain.swift","parallel":"fused_evaluation/RepeatMain.swift","cache":"segment_sweep_cache/main.swift","receipts":"clearance_receipts/main.swift","hints":"working_hint/main.swift","convergence":"physical_convergence/main.swift"}[args.kind]
    (snapshot/"main.swift").write_bytes((tool/test).read_bytes())
    if convergence:(snapshot/"ConvergenceTrace.swift").write_bytes((tool/"physical_convergence/Trace.swift").read_bytes())
    files=sorted(snapshot.iterdir())
    binary=stage/(REPO.name+"-speed-screen")
    command=["xcrun","swiftc","-O","-whole-module-optimization","-Xcc","-DACCELERATE_NEW_LAPACK","-module-cache-path",str(stage/"module-cache"),*map(str,files),"-o",str(binary)]
    checkpoint=REPO/".context/strong-owl-live-physics-solver-foundation/clav-contact-step/checkpoint.json"
    prior=REPO/".context/strong-owl-live-physics-accepted-profile/native/after-1.json"
    inputs=[*files,checkpoint,prior,Path(__file__),REPO/"Hangboards/clavellium-training-block/assets/primary.physics.json"]
    for folder in ["fused_evaluation","parallel_queries","segment_sweep_cache","clearance_receipts","working_hint","physical_convergence","parallel_sweep"]:
        inputs.extend(p for p in (tool/folder).iterdir() if p.is_file())
    (stage/"provenance.json").write_text(json.dumps({"owner":REPO.name,"baselineCommit":BASE,"arguments":vars(args),"command":command,"hashes":{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
    owner=OwnedCommands(REPO.name,stage)
    for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,owner.interrupted)
    try:
        status=owner.run("compile",["perl","-e","alarm 150; exec @ARGV",*command],stage/"compile.log",dict(os.environ))
        if not status:status=owner.run("run",["perl","-e","alarm 1800; exec @ARGV",str(binary),str(stage),str(checkpoint),str(prior)],stage/"run.log",dict(os.environ))
        print((stage/("run.log" if (stage/"run.log").exists() else "compile.log")).read_text())
    finally:owner.cleanup()
    return status
if __name__=="__main__":raise SystemExit(main())
