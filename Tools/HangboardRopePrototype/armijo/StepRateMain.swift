import Foundation
import simd
import Darwin

let root=URL(fileURLWithPath:CommandLine.arguments[1])
let prior=try decodeCheckpointJSON(Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2])))
let priorSteps=prior["steps"] as! [[String:Any]]
let arguments=CommandLine.arguments
let hz=Int(arguments[arguments.firstIndex(of:"--candidate-hz")!+1])!
let preflight=arguments.contains("--preflight")
precondition(hz==240 || hz==120)
precondition(!preflight || hz==240)
let factor=240/hz,turnSteps=hz,returnSteps=hz*5/4
let count=preflight ? 20:turnSteps+returnSteps
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
let upright=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
let turned=simd_quatd(angle:Double.pi/6,axis:SIMD3<Double>(0,0,1))
let seed=try RopeThreadedSeed.make(input:input,profileID:input.profiles[0].id,orientation:upright,collider:collider)
let initial=try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
var control=initial,candidate=initial,records:[[String:Any]]=[]
var result:[String:Any]=["owner":"strong-owl-live-physics","adopted":false,"candidateHz":hz,
    "controlHz":240,"preflight":preflight,"armijoEnabled":false]
var settledPhases=Set<Int>()

func serialize(_ d:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:d,options:[.sortedKeys])}
func persist(_ failure:String?=nil)throws {
    result["steps"]=records;result["measuredSteps"]=records.count
    if let failure {result["failure"]=failure}
    try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys,.prettyPrinted]).write(to:root.appendingPathComponent("result.json"))
}
func difference(_ a:RopeDynamicsSolver,_ b:RopeDynamicsSolver)->Double {
    var d=abs(a.state.boardHeight-b.state.boardHeight)
    for r in a.state.ropes.indices {for i in a.state.ropes[r].positions.indices {
        d=max(d,simd_distance(a.state.ropes[r].positions[i],b.state.ropes[r].positions[i]))
    }}
    return d
}
func run(_ x:inout RopeDynamicsSolver,_ dt:Double,_ target:simd_quatd)throws->(Double,[[String:Any]],RopeFrameSnapshot) {
    ArmijoTrace.collectDerivatives=false;ArmijoTrace.collectOracleBranches=false
    ArmijoTrace.corrections=[];alarm(10)
    defer {alarm(0)}
    let start=ProcessInfo.processInfo.systemUptime
    let frame=try x.step(dt:dt,targetOrientation:target)
    return (ProcessInfo.processInfo.systemUptime-start,ArmijoTrace.corrections,frame)
}
func check(_ x:RopeDynamicsSolver)throws->[String:Any] {
    let history=x.foundationCheckpoint()["history"] as! [[Double]]
    let m=try RopeSimulationMetrics.measure(state:x.state,input:input,collider:collider,boardHistory:history.map{$0[1]})
    guard m.geometryAccepted else {throw RopePhysicsError.invalid("uncached original mesh/material gate")}
    for r in x.state.ropes.indices {
        let a=initial.state.ropes[r],b=x.state.ropes[r]
        guard a.id==b.id,a.radius==b.radius,a.linearMass==b.linearMass,a.restLengths==b.restLengths,
            a.supports==b.supports,a.attachments==b.attachments,a.portals==b.portals,a.channelSegments==b.channelSegments else {
            throw RopePhysicsError.invalid("immutable material/bindings")
        }
    }
    return ["geometryAccepted":m.geometryAccepted,"strain":m.maximumLocalStrain,"lengthError":m.totalLengthError,
        "clearanceMargin":m.minimumClearanceMargin,"speed":m.maximumSpeed,"boardDisplacement":m.boardDisplacement]
}
func reference(_ checkpoint:Data,_ target:simd_quatd)throws->(RopeDynamicsSolver,[String:Any]) {
    var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint,strict:true)
    var caps=0,retries=0,qps=0,traces:[[[String:Any]]]=[]
    for _ in 0..<factor {
        traces.append(try run(&strict,1.0/240,target).1)
        caps += strict.reviewStepCaps;retries += strict.reviewStepRetries;qps += strict.reviewStepCorrections
    }
    return (strict,["caps":caps,"retries":retries,"qps":qps,"traces":traces])
}
func quantile(_ values:[Double],_ q:Double)->Double {let v=values.sorted();return v[Int(ceil(q*Double(v.count-1)))]}
do {
    for step in 1...count {
        let target=step<=turnSteps ? turned:upright,phase=step<=turnSteps ? 0:1
        let checkpoint=try serialize(candidate.bundleCheckpoint())
        try checkpoint.write(to:root.appendingPathComponent("pending-input.json"))
        result["attemptedSteps"]=step;result["pendingPhase"]=phase
        try persist()
        var controlSeconds=0.0,controlQPs=0,controlCaps=0,controlRetries=0
        func controlRun()throws {
            for substep in 0..<factor {
                let runResult=try run(&control,1.0/240,target)
                controlSeconds += runResult.0;controlQPs += control.reviewStepCorrections
                controlCaps += control.reviewStepCaps;controlRetries += control.reviewStepRetries
                let index=(step-1)*factor+substep
                let old=(priorSteps[index]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]
                guard runResult.1.count==old.count else {throw RopePhysicsError.invalid("control correction count identity")}
                for (a,b) in zip(runResult.1,old) {for key in ["alpha","movement","strain"] {
                    guard (a[key] as! Double)==b[key] else {throw RopePhysicsError.invalid("control numeric identity \(index+1) \(key)")}
                }}
            }
        }
        let measured:(Double,[[String:Any]],RopeFrameSnapshot)
        if step%2==0 {measured=try run(&candidate,1.0/Double(hz),target);try controlRun()}
        else {try controlRun();measured=try run(&candidate,1.0/Double(hz),target)}
        var record:[String:Any]=["step":step,"controlStep":step*factor,"phase":phase,
            "candidateSeconds":measured.0,"controlSeconds":controlSeconds,
            "candidateQPs":candidate.reviewStepCorrections,"controlQPs":controlQPs,
            "candidateCaps":candidate.reviewStepCaps,"controlCaps":controlCaps,
            "candidateRetries":candidate.reviewStepRetries,"controlRetries":controlRetries,
            "trace":measured.1,"difference":difference(control,candidate),"settled":measured.2.settled]
        records.append(record)
        record["metrics"]=try check(candidate);records[records.count-1]=record
        let candidateTime=candidate.foundationCheckpoint()["time"] as! Double
        let controlTime=control.foundationCheckpoint()["time"] as! Double
        guard abs(candidateTime-controlTime)<1e-12 else {throw RopePhysicsError.invalid("matched elapsed time")}
        guard candidate.reviewStepCaps==0,candidate.reviewStepRetries==0,difference(control,candidate)<=0.00005 else {
            throw RopePhysicsError.invalid("matched-time pose/cap/retry step \(step)")
        }
        if hz==240 {
            guard try serialize(candidate.bundleCheckpoint())==serialize(control.bundleCheckpoint()) else {
                throw RopePhysicsError.invalid("same-rate complete persisted checkpoint identity")
            }
            record["sameRateCheckpointIdentity"]=true
        }
        if step<=20 || step%10==0 {
            let (strict,evidence)=try reference(checkpoint,target)
            record["strictReference"]=evidence;record["strictDifference"]=difference(strict,candidate)
            records[records.count-1]=record
            guard (evidence["caps"] as! Int)==0,(evidence["retries"] as! Int)==0,
                difference(strict,candidate)<=0.00005 else {throw RopePhysicsError.invalid("strict matched-time reference step \(step)")}
        }
        if !preflight,measured.2.settled,!settledPhases.contains(phase) {
            var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:serialize(candidate.bundleCheckpoint()),strict:true)
            var frames:[[String:Any]]=[]
            for _ in 0..<factor {
                let extra=try run(&strict,1.0/240,target).2
                frames.append(["settled":extra.settled,"speed":extra.metrics.maximumSpeed,
                    "boardHistoryDisplacement":extra.metrics.boardDisplacement,"caps":strict.reviewStepCaps,"retries":strict.reviewStepRetries])
                record["falseSettleChecks"]=frames;records[records.count-1]=record
                guard strict.reviewStepCaps==0,strict.reviewStepRetries==0,extra.settled else {
                    throw RopePhysicsError.invalid("strict false-settle continuation")
                }
            }
            settledPhases.insert(phase)
        }
        if !preflight,(step>turnSteps-hz/4 && step<=turnSteps) || (!preflight && step>count-hz/4) {
            guard measured.2.settled else {throw RopePhysicsError.invalid("quarter-second settled tail")}
        }
        records[records.count-1]=record
        if step<=20 || step%10==0 {try persist();print("checkpoint",step,"difference",difference(control,candidate),"QPs",candidate.reviewStepCorrections);fflush(stdout)}
        if step==20 {result["stageOnePass"]=true;try persist()}
    }
    if !preflight {guard settledPhases.count==2 else {throw RopePhysicsError.invalid("both settled destinations")}}
    try serialize(candidate.bundleCheckpoint()).write(to:root.appendingPathComponent("final-candidate.json"))
    try serialize(control.bundleCheckpoint()).write(to:root.appendingPathComponent("final-control.json"))
    let times=records.map{$0["candidateSeconds"] as! Double},batchSize=hz/60
    let batches=stride(from:0,to:times.count,by:batchSize).filter{$0+batchSize<=times.count}.map{times[$0..<$0+batchSize].reduce(0,+)}
    result["p50Seconds"]=quantile(times,0.5);result["p95Seconds"]=quantile(times,0.95);result["maxSeconds"]=times.max()!
    result["estimatedP95EngineBatchSeconds"]=quantile(batches,0.95)
    result["engineSeconds"]=times.reduce(0,+);result["simulatedSeconds"]=Double(count)/Double(hz)
    result["accuracyPass"]=true;result["preflightPass"]=preflight
    result["hostRealtimePass"] = !preflight && times.reduce(0,+)<Double(count)/Double(hz) &&
        quantile(times,0.95)<(hz==120 ? 0.008:0.004) && quantile(batches,0.95)<1.0/60
    try persist();print("PASS accuracy; preflight",preflight,"p95",quantile(times,0.95))
    if !preflight && !(result["hostRealtimePass"] as! Bool) {exit(3)}
} catch {try persist(String(describing:error));print("FAIL step-rate screen",error);exit(2)}
