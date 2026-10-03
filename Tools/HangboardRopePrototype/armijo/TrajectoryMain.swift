import Foundation
import simd
import Darwin

let root=URL(fileURLWithPath:CommandLine.arguments[1])
let prior=try decodeCheckpointJSON(Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2])))
let priorSteps=prior["steps"] as! [[String:Any]]
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
let upright=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
let turned=simd_quatd(angle:Double.pi/6,axis:SIMD3<Double>(0,0,1))
let seed=try RopeThreadedSeed.make(input:input,profileID:input.profiles[0].id,orientation:upright,collider:collider)
let initial=try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
var control=initial,candidate=initial
candidate.armijoExperiment=true
var records:[[String:Any]]=[]
var result:[String:Any]=["owner":"strong-owl-live-physics","adopted":false,"sigma":RopeArmijo.sigma,
    "plan":"first20 strict/oracle then fixed540 turn240 return300","oracleAlphas":[1e-3,1e-4,1e-5,1e-6,1e-7]]
var settledPhases=Set<Int>()

func serialize(_ d:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:d,options:[.sortedKeys])}
func persist(_ failure:String?=nil)throws {
    result["steps"]=records;result["attemptedMeasuredSteps"]=records.count
    result["derivativeFailures"]=ArmijoTrace.derivativeFailures
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
func run(_ x:inout RopeDynamicsSolver,_ target:simd_quatd)throws->(Double,[[String:Any]],RopeFrameSnapshot) {
    ArmijoTrace.collectDerivatives=x.armijoExperiment
    ArmijoTrace.collectOracleBranches=x.verifyArmijoDerivative
    ArmijoTrace.corrections=[];alarm(10)
    defer {alarm(0)}
    let start=ProcessInfo.processInfo.systemUptime
    let frame=try x.step(dt:1.0/240,targetOrientation:target)
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
func decisionIdentity(_ a:[[String:Any]],_ b:[[String:Any]])throws {
    guard a.count==b.count else {throw RopePhysicsError.invalid("oracle copy count identity")}
    for (x,y) in zip(a,b) {for key in ["alpha","movement","strain","rows","armijoRejected","originalRejected"] {
        guard (x[key] as! NSNumber)==(y[key] as! NSNumber) else {throw RopePhysicsError.invalid("oracle decision identity \(key)")}
    }}
}
func quantile(_ values:[Double],_ q:Double)->Double {let v=values.sorted();return v[Int(ceil(q*Double(v.count-1)))]}

do {
    try ambiguityFixtures();result["ambiguityFixturesPass"]=true
    for step in 1...540 {
        let phase=step<=240 ? 0:1,target=step<=240 ? turned:upright
        let checkpoint=try serialize(candidate.bundleCheckpoint())
        try checkpoint.write(to:root.appendingPathComponent("pending-input.json"))
        let sampled=step<=20 || step%20==0
        var verified:RopeDynamicsSolver?,oracleTrace:[[String:Any]]=[]
        if sampled {
            var copy=candidate;copy.verifyArmijoDerivative=true
            oracleTrace=try run(&copy,target).1;verified=copy
        }
        let originalRun:(Double,[[String:Any]],RopeFrameSnapshot),candidateRun:(Double,[[String:Any]],RopeFrameSnapshot)
        if step%2==0 {candidateRun=try run(&candidate,target);originalRun=try run(&control,target)}
        else {originalRun=try run(&control,target);candidateRun=try run(&candidate,target)}
        var record:[String:Any]=["step":step,"phase":phase,"originalSeconds":originalRun.0,"candidateSeconds":candidateRun.0,
            "originalQPs":control.reviewStepCorrections,"candidateQPs":candidate.reviewStepCorrections,
            "originalCaps":control.reviewStepCaps,"candidateCaps":candidate.reviewStepCaps,
            "originalRetries":control.reviewStepRetries,"candidateRetries":candidate.reviewStepRetries,
            "propagatedDifference":difference(control,candidate),"trace":candidateRun.1,"settled":candidateRun.2.settled]
        records.append(record)
        // Failures retain the offending record, complete input and partial history.
        record["metrics"]=try check(candidate)
        records[records.count-1]=record
        guard candidate.reviewStepCaps<=control.reviewStepCaps,candidate.reviewStepRetries<=control.reviewStepRetries,
            difference(control,candidate)<=0.00005 else {throw RopePhysicsError.invalid("propagated pose/cap/retry step \(step)")}
        let old=(priorSteps[step-1]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]
        guard originalRun.1.count==old.count else {throw RopePhysicsError.invalid("control prefix count identity")}
        for (x,y) in zip(originalRun.1,old) {for key in ["alpha","movement","strain"] {
            guard (x[key] as! Double)==y[key] else {throw RopePhysicsError.invalid("control prefix numeric identity \(step) \(key)")}
        }}
        if let verified {
            guard try serialize(verified.bundleCheckpoint())==serialize(candidate.bundleCheckpoint()) else {
                throw RopePhysicsError.invalid("oracle full checkpoint identity")
            }
            try decisionIdentity(oracleTrace,candidateRun.1)
            record["oracleTrace"]=oracleTrace;record["oracleIdentity"]=true
            var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint,strict:true)
            let reference=try run(&strict,target)
            record["strictQPs"]=strict.reviewStepCorrections;record["strictCaps"]=strict.reviewStepCaps
            record["strictRetries"]=strict.reviewStepRetries;record["strictDifference"]=difference(strict,candidate)
            record["strictTrace"]=reference.1
            records[records.count-1]=record
            guard strict.reviewStepCaps==0,strict.reviewStepRetries==0,difference(strict,candidate)<=0.00005 else {
                throw RopePhysicsError.invalid("strict same-input reference step \(step)")
            }
        }
        if candidateRun.2.settled && !settledPhases.contains(phase) {
            var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,
                data:serialize(candidate.bundleCheckpoint()),strict:true)
            let extra=try run(&strict,target).2
            record["falseSettleCheck"]=["speed":extra.metrics.maximumSpeed,"poseDifference":difference(strict,candidate),
                "boardHistoryDisplacement":extra.metrics.boardDisplacement,"settled":extra.settled,
                "caps":strict.reviewStepCaps,"retries":strict.reviewStepRetries]
            records[records.count-1]=record
            guard strict.reviewStepCaps==0,strict.reviewStepRetries==0,extra.settled,
                difference(strict,candidate)<0.0001 else {throw RopePhysicsError.invalid("strict false-settle check")}
            settledPhases.insert(phase)
        }
        if (181...240).contains(step) || (481...540).contains(step) {
            guard candidateRun.2.settled else {throw RopePhysicsError.invalid("last60 stability step \(step)")}
        }
        records[records.count-1]=record
        if sampled {try persist();print("checkpoint",step,"QPs",candidate.reviewStepCorrections,"difference",difference(control,candidate));fflush(stdout)}
        if step==20 {result["stageOnePass"]=true;try persist()}
    }
    guard settledPhases.count==2 else {throw RopePhysicsError.invalid("both settled destinations")}
    let times=records.map{$0["candidateSeconds"] as! Double},originalTimes=records.map{$0["originalSeconds"] as! Double}
    result["candidateP50Seconds"]=quantile(times,0.5);result["candidateP95Seconds"]=quantile(times,0.95)
    result["originalP95Seconds"]=quantile(originalTimes,0.95)
    result["candidateTotalSeconds"]=times.reduce(0,+);result["originalTotalSeconds"]=originalTimes.reduce(0,+)
    result["simulatedSeconds"]=540.0/240;result["trajectoryAccuracyPass"]=true
    result["hostRealtimePass"]=quantile(times,0.95)<0.004
    try persist();print("PASS trajectory accuracy; p95",quantile(times,0.95))
    if quantile(times,0.95)>=0.004 {exit(3)}
} catch {try persist(String(describing:error));print("FAIL trajectory",error);exit(2)}
