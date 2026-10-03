import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any],sha=raw["modelSHA256"] as! String
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:sha)
let controlInput=try ControlRopePhysicsDescriptor.decode(data).validated(modelSHA256:sha)
let strictInput=try StrictRopePhysicsDescriptor.decode(data).validated(modelSHA256:sha)
let collider=try RopeTriangleCollider(input:input),controlCollider=try ControlRopeTriangleCollider(input:controlInput)
let strictCollider=try StrictRopeTriangleCollider(input:strictInput)
let upright=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1)),target=simd_quatd(angle:Double.pi/6,axis:SIMD3<Double>(0,0,1))
let seed=try RopeThreadedSeed.make(input:input,profileID:input.profiles[0].id,orientation:upright,collider:collider)
let controlSeed=try ControlRopeThreadedSeed.make(input:controlInput,profileID:controlInput.profiles[0].id,orientation:upright,collider:controlCollider)
var candidate=try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
var control=try ControlRopeDynamicsSolver.prepareDisplay(input:controlInput,state:controlSeed,collider:controlCollider).solver
func serialize(_ value:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys])}
var reports:[[String:Any]]=[],referenceDifference=0.0
func persist(_ failure:String?)throws {
    var result:[String:Any]=["owner":"strong-owl-live-physics","prefixSteps":139,"pairedRuns":reports,"strictReferenceDifferenceMeters":referenceDifference,
        "fixedMaximumRatio":0.8,"adopted":false,"scope":"native step140, original cold-per-step nearest discovery plus held/repaired faces; physical convergence; host-only"]
    if reports.count==7 {let ratios=reports.map{$0["ratio"] as! Double}.sorted();result["medianRatio"]=ratios[3];result["performancePassed"]=ratios[3]<=0.8}
    if let failure {result["failure"]=failure}
    try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
}
func distance(_ x:RopeSimulationState,_ y:ControlRopeSimulationState)->Double {
    var d=abs(x.boardHeight-y.boardHeight)
    for r in x.ropes.indices {for i in x.ropes[r].positions.indices {d=max(d,simd_distance(x.ropes[r].positions[i],y.ropes[r].positions[i]))}}
    return d
}
func strictDistance(_ x:RopeSimulationState,_ y:StrictRopeSimulationState)->Double {
    var d=abs(x.boardHeight-y.boardHeight)
    for r in x.ropes.indices {for i in x.ropes[r].positions.indices {d=max(d,simd_distance(x.ropes[r].positions[i],y.ropes[r].positions[i]))}}
    return d
}
do {
    // Disabled hook must preserve the actual current private checkpoint exactly.
    for step in 1...139 {
        alarm(10);_ = try candidate.step(dt:1.0/240,targetOrientation:target);_ = try control.step(dt:1.0/240,targetOrientation:target);alarm(0)
        guard try serialize(candidate.bundleCheckpoint())==serialize(control.bundleCheckpoint()),
            candidate.reviewStepCorrections==control.reviewStepCorrections,candidate.reviewStepCaps==control.reviewStepCaps,
            candidate.reviewStepRetries==control.reviewStepRetries else {throw RopePhysicsError.invalid("disabled hook changed prefix \(step)")}
        if step%20==0 {print("prefix",step,"bit-identical");fflush(stdout)}
    }
    let checkpoint=try serialize(control.bundleCheckpoint())
    try checkpoint.write(to:root.appendingPathComponent("before.json"))
    candidate=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint)
    control=try ControlRopeDynamicsSolver.restoreBundle(input:controlInput,collider:controlCollider,data:checkpoint)
    guard try serialize(candidate.bundleCheckpoint())==checkpoint,try serialize(control.bundleCheckpoint())==checkpoint else {throw RopePhysicsError.invalid("checkpoint round-trip changed private input")}
    candidate.setBundleExperiment(true)
    var strict=try StrictRopeDynamicsSolver.restoreBundle(input:strictInput,collider:strictCollider,data:checkpoint,strict:true)
    alarm(10);let strictFrame=try strict.step(dt:1.0/240,targetOrientation:target);alarm(0)
    guard strictFrame.metrics.geometryAccepted,strict.reviewStepCaps==0,strict.reviewStepRetries==0 else {throw RopePhysicsError.invalid("strict reference unconverged")}
    for index in 0..<7 {
        var x=candidate,y=control
        var cx=0.0,cy=0.0
        var frame:RopeFrameSnapshot?,original:ControlRopeFrameSnapshot?
        func runCandidate()throws {let t=ProcessInfo.processInfo.systemUptime;frame=try x.step(dt:1.0/240,targetOrientation:target);cx=ProcessInfo.processInfo.systemUptime-t}
        func runControl()throws {let t=ProcessInfo.processInfo.systemUptime;original=try y.step(dt:1.0/240,targetOrientation:target);cy=ProcessInfo.processInfo.systemUptime-t}
        alarm(10);if index%2==0 {try runControl();try runCandidate()} else {try runCandidate();try runControl()};alarm(0)
        let physical=try RopeSimulationMetrics.measure(state:x.state,input:input,collider:collider,boardHistory:[x.state.boardHeight])
        let diff=distance(x.state,y.state),strictDiff=strictDistance(x.state,strict.state)
        referenceDifference=max(referenceDifference,strictDiff)
        let record:[String:Any]=["run":index,"candidateSeconds":cx,"controlSeconds":cy,"ratio":cx/cy,"bundle":x.bundleReport,
            "candidateQPs":x.reviewStepCorrections,"controlQPs":y.reviewStepCorrections,"candidateCaps":x.reviewStepCaps,"candidateRetries":x.reviewStepRetries,
            "originalDifferenceMeters":diff,"strictDifferenceMeters":strictDiff,"independentMeshAccepted":physical.geometryAccepted,
            "meshClearanceMargin":physical.minimumClearanceMargin,"strain":physical.maximumLocalStrain,"lengthError":physical.totalLengthError]
        reports.append(record);try persist(nil)
        guard frame!.metrics.geometryAccepted,original!.metrics.geometryAccepted,physical.geometryAccepted,diff<=0.00005,strictDiff<=0.00005,
            x.reviewStepCaps<=y.reviewStepCaps,x.reviewStepRetries<=y.reviewStepRetries else {throw RopePhysicsError.invalid("checkpoint physical/reference/work gate")}
        for r in x.state.ropes.indices {
            let a=seed.ropes[r],b=x.state.ropes[r]
            guard a.id==b.id,a.radius==b.radius,a.linearMass==b.linearMass,a.restLengths==b.restLengths,a.supports==b.supports,
                a.attachments==b.attachments,a.portals==b.portals,a.channelSegments==b.channelSegments else {throw RopePhysicsError.invalid("material/bindings changed")}
        }
        print("pair",index,"ratio",cx/cy,"QPs",x.reviewStepCorrections,"strict um",strictDiff*1e6,"bundle",x.bundleReport);fflush(stdout)
    }
    let median=reports.map{$0["ratio"] as! Double}.sorted()[3]
    guard median<=0.8 else {throw RopePhysicsError.invalid("fixed complete-step ratio \(median) exceeds0.8")}
    print("PASS checkpoint physical/reference and local speed screen",median)
} catch {try persist(String(describing:error));print("FAIL",error);exit(2)}
