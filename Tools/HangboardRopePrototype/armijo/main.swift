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
let seed=try RopeThreadedSeed.make(input:input,profileID:input.profiles[0].id,orientation:upright,collider:collider)
var initial=try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
let target=simd_quatd(angle:Double.pi/6,axis:SIMD3<Double>(0,0,1))
var result:[String:Any]=["owner":"strong-owl-live-physics","adopted":false,"sigma":RopeArmijo.sigma,"step":109]
var pairs:[[String:Any]]=[]
func serialize(_ d:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:d,options:[.sortedKeys])}
func persist(_ failure:String?)throws {
    result["pairs"]=pairs
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
func run(_ x:inout RopeDynamicsSolver)throws->(Double,[[String:Any]]) {
    ArmijoTrace.collectDerivatives=x.armijoExperiment
    ArmijoTrace.collectOracleBranches=x.verifyArmijoDerivative
    ArmijoTrace.corrections=[];alarm(10)
    let start=ProcessInfo.processInfo.systemUptime
    _ = try x.step(dt:1.0/240,targetOrientation:target)
    let seconds=ProcessInfo.processInfo.systemUptime-start
    alarm(0);return (seconds,ArmijoTrace.corrections)
}
func check(_ x:RopeDynamicsSolver)throws->[String:Any] {
    let history=x.foundationCheckpoint()["history"] as! [[Double]]
    let m=try RopeSimulationMetrics.measure(state:x.state,input:input,collider:collider,boardHistory:history.map{$0[1]})
    guard m.geometryAccepted else {throw RopePhysicsError.invalid("uncached original geometry failure")}
    for r in x.state.ropes.indices {
        let a=initial.state.ropes[r],b=x.state.ropes[r]
        guard a.id==b.id,a.radius==b.radius,a.linearMass==b.linearMass,a.restLengths==b.restLengths,
            a.supports==b.supports,a.attachments==b.attachments,a.portals==b.portals,a.channelSegments==b.channelSegments else {
            throw RopePhysicsError.invalid("material/bindings changed")
        }
    }
    return ["geometryAccepted":m.geometryAccepted,"strain":m.maximumLocalStrain,"lengthError":m.totalLengthError,
        "clearanceMargin":m.minimumClearanceMargin,"speed":m.maximumSpeed]
}
func fixtures()throws {
    // One-sided abs derivative catches the zero-residual kink.
    for residual in [-0.2,0,0.2] {
        let rate = -0.3,h=1e-7
        let expected=(abs(residual+h*rate)-abs(residual))/h
        guard abs(RopeArmijo.lengthSlope(residual:residual,rate:rate)-expected)<1e-8 else {
            throw RopePhysicsError.invalid("one-sided length derivative")
        }
    }
    guard !RopeArmijo.inactiveHinge(0),!RopeArmijo.inactiveHinge(Double.nan),!RopeArmijo.inactiveHinge(1e-12),
          RopeArmijo.inactiveHinge(-1e-12) else {throw RopePhysicsError.invalid("hinge boundary")}
    let positions=[SIMD3<Double>(0,0,0),SIMD3<Double>(1,0,0),SIMD3<Double>(2,0,0)]
    let rope=RopeChainState(id:"fixture",radius:0.0035,linearMass:0.01,restLengths:[1,1],
        positions:positions,previousPositions:positions,velocities:Array(repeating:.zero,count:3),
        supports:[0:.zero],attachments:[1:.zero],portals:[:],channelSegments:[:])
    let correction=SIMD3<Double>(7,8,9)
    guard RopeArmijo.displacement(rope,0,correction,0.4) == .zero,
          RopeArmijo.displacement(rope,1,correction,0.4)==SIMD3(0,0.4,0),
          RopeArmijo.displacement(rope,2,correction,0.4)==correction else {throw RopePhysicsError.invalid("actual trial displacement")}
}
do {
    try fixtures();result["fixturesPass"]=true
    if CommandLine.arguments.contains("--fixtures-only") {print("PASS Armijo fixtures");exit(0)}
    for step in 1...108 {
        let record=try run(&initial).1
        let old=(priorSteps[step-1]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]
        guard record.count==old.count else {throw RopePhysicsError.invalid("prefix count identity")}
        for (a,b) in zip(record,old) {
            for key in ["movement","alpha","strain"] {
                guard (a[key] as! Double)==b[key] else {
                    throw RopePhysicsError.invalid("prefix numeric identity step \(step), \(key): \(a[key]!) vs \(b[key]!)")
                }
            }
        }
    }
    result["prefixIdentitySteps"]=108
    let checkpoint=try serialize(initial.bundleCheckpoint())
    try checkpoint.write(to:root.appendingPathComponent("checkpoint.json"))
    var original=initial,candidate=initial
    candidate.armijoExperiment=true
    let control=try run(&original),probe=try run(&candidate)
    result["originalTrace"]=control.1;result["candidateTrace"]=probe.1
    result["originalQPs"]=original.reviewStepCorrections;result["candidateQPs"]=candidate.reviewStepCorrections
    result["currentDifferenceMeters"]=difference(original,candidate)
    result["candidateMetrics"]=try check(candidate)
    guard candidate.reviewStepCaps<=original.reviewStepCaps,candidate.reviewStepRetries<=original.reviewStepRetries,
          difference(original,candidate)<=0.00005 else {throw RopePhysicsError.invalid("current comparison/cap/retry")}
    var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint,strict:true)
    let strictTrace=try run(&strict).1
    result["strictTrace"]=strictTrace;result["strictDifferenceMeters"]=difference(strict,candidate)
    result["strictConverged"]=strict.reviewStepCaps==0
    result["strictRetries"]=strict.reviewStepRetries
    guard strict.reviewStepCaps==0,strict.reviewStepRetries==0,difference(strict,candidate)<=0.00005 else {
        throw RopePhysicsError.invalid("strict reference comparison/convergence")
    }
    guard candidate.reviewStepCorrections<=5 else {throw RopePhysicsError.invalid("fixed <=5-QP work gate")}
    for iteration in 0..<7 {
        var a=initial,b=initial;b.armijoExperiment=true
        let ca:(Double,[[String:Any]]),cb:(Double,[[String:Any]])
        if iteration%2==0 {ca=try run(&a);cb=try run(&b)} else {cb=try run(&b);ca=try run(&a)}
        guard try serialize(a.bundleCheckpoint())==serialize(original.bundleCheckpoint()),
              try serialize(b.bundleCheckpoint())==serialize(candidate.bundleCheckpoint()) else {
            throw RopePhysicsError.invalid("paired determinism")
        }
        _ = try check(b)
        pairs.append(["originalSeconds":ca.0,"candidateSeconds":cb.0,"ratio":cb.0/ca.0])
    }
    let ratios=pairs.map{$0["ratio"] as! Double}.sorted(),median=ratios[3]
    result["medianRatio"]=median;result["workAndAccuracyPass"]=true
    try persist(nil)
    guard median<=0.80 else {throw RopePhysicsError.invalid("fixed median <=0.80 speed gate")}
    result["checkpointPass"]=true;try persist(nil)
    print("PASS isolated step109; QPs",candidate.reviewStepCorrections,"medianRatio",median,"strictDifference",difference(strict,candidate))
} catch {try persist(String(describing:error));print("FAIL isolated step109",error);exit(2)}
