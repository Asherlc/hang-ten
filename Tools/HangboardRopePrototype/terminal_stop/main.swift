import Foundation
import simd
import Darwin

let root=URL(fileURLWithPath:CommandLine.arguments[1])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let controlInput=try ControlRopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input),controlCollider=try ControlRopeTriangleCollider(input:controlInput)
let upright=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
let target=simd_quatd(angle:Double.pi/6,axis:SIMD3<Double>(0,0,1))
let seed=try RopeThreadedSeed.make(input:input,profileID:input.profiles[0].id,orientation:upright,collider:collider)
let controlSeed=try ControlRopeThreadedSeed.make(input:controlInput,profileID:controlInput.profiles[0].id,orientation:upright,collider:controlCollider)
var candidate=try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
var control=try ControlRopeDynamicsSolver.prepareDisplay(input:controlInput,state:controlSeed,collider:controlCollider).solver
func compare(_ x:RopeDynamicsSolver,_ y:ControlRopeDynamicsSolver)throws->Double {
    var difference=abs(x.state.boardHeight-y.state.boardHeight)
    guard x.state.orientation.vector==y.state.orientation.vector,
          x.state.ropes.count==y.state.ropes.count,
          x.reviewStepCaps<=y.reviewStepCaps,x.reviewStepRetries<=y.reviewStepRetries,
          x.reviewTerminalStops<=1,x.reviewTerminalStops==0 || x.reviewStepCorrections>=2 else {
        throw RopePhysicsError.invalid("orientation, new cap/retry, or first-correction terminal stop")
    }
    for r in x.state.ropes.indices {
        let a=x.state.ropes[r],b=y.state.ropes[r]
        guard a.id==b.id,a.radius==b.radius,a.linearMass==b.linearMass,
              a.restLengths==b.restLengths,a.supports==b.supports,a.attachments==b.attachments,
              a.portals==b.portals,a.channelSegments==b.channelSegments else {
            throw RopePhysicsError.invalid("immutable material/bindings changed")
        }
        for i in a.positions.indices {difference=max(difference,simd_distance(a.positions[i],b.positions[i]))}
    }
    guard difference<=0.00005 else {throw RopePhysicsError.invalid("propagated pose difference \(difference)")}
    return difference
}
var prefix:[[String:Any]]=[],reports:[[String:Any]]=[]
func persist(_ failure:String?=nil)throws {
    let ratios=reports.map{$0["ratio"] as! Double}.sorted()
    var result:[String:Any]=["owner":"strong-owl-live-physics","prefix":prefix,"pairedRuns":reports,
        "fixedMaximumRatio":0.8,"poseGateMeters":0.00005,"adopted":false,
        "scope":"complete actual-seed step140 after independently propagated current-source prefix; isolated changed convergence semantics; host-only"]
    if reports.count==7 {result["medianRatio"]=ratios[3];result["performancePassed"]=ratios[3]<=0.8;result["accuracyPassed"]=true}
    if let failure {result["failure"]=failure}
    try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
}
do {
    for step in 1...139 {
        alarm(10)
        let a=try candidate.step(dt:1.0/240,targetOrientation:target)
        let b=try control.step(dt:1.0/240,targetOrientation:target)
        alarm(0)
        guard a.metrics.geometryAccepted,b.metrics.geometryAccepted else {throw RopePhysicsError.invalid("prefix physics")}
        let difference=try compare(candidate,control)
        prefix.append(["step":step,"differenceMeters":difference,"corrections":candidate.reviewStepCorrections,
            "controlCorrections":control.reviewStepCorrections,"terminalStops":candidate.reviewTerminalStops])
        if step%20==0 {print("prefix",step,"difference",difference);fflush(stdout)}
        try persist()
    }
    for index in 0..<7 {
        var x=candidate,y=control
        var candidateSeconds=0.0,controlSeconds=0.0
        func measureCandidate()throws {
            let t=ProcessInfo.processInfo.systemUptime
            let f=try x.step(dt:1.0/240,targetOrientation:target)
            candidateSeconds=ProcessInfo.processInfo.systemUptime-t
            guard f.metrics.geometryAccepted else {throw RopePhysicsError.invalid("candidate physics")}
        }
        func measureControl()throws {
            let t=ProcessInfo.processInfo.systemUptime
            let f=try y.step(dt:1.0/240,targetOrientation:target)
            controlSeconds=ProcessInfo.processInfo.systemUptime-t
            guard f.metrics.geometryAccepted else {throw RopePhysicsError.invalid("control physics")}
        }
        alarm(10)
        if index%2==0 {try measureControl();try measureCandidate()} else {try measureCandidate();try measureControl()}
        alarm(0)
        let difference=try compare(x,y)
        guard x.reviewStepCorrections==2,y.reviewStepCorrections==2,x.reviewTerminalStops==1,
              x.reviewStepCaps==0,x.reviewStepRetries==0,y.reviewStepCaps==0,y.reviewStepRetries==0 else {
            throw RopePhysicsError.invalid("fixed two-fresh-QP terminal discriminator changed")
        }
        reports.append(["run":index,"controlSeconds":controlSeconds,"candidateSeconds":candidateSeconds,
            "ratio":candidateSeconds/controlSeconds,"differenceMeters":difference,
            "corrections":x.reviewStepCorrections,"terminalStops":x.reviewTerminalStops])
        print("pair",index,controlSeconds,candidateSeconds,"difference",difference);fflush(stdout)
        try persist()
    }
    let median=reports.map{$0["ratio"] as! Double}.sorted()[3]
    print(median<=0.8 ? "PASS complete-step terminal discriminator":"FAIL complete-step terminal discriminator",median)
    if median>0.8 {exit(2)}
} catch {
    try persist(String(describing:error));print("FAIL",error);fflush(stdout);exit(2)
}
