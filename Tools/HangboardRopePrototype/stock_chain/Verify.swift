import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let descriptor=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[3]))
let raw=try JSONSerialization.jsonObject(with:descriptor) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(descriptor).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
let sourceURL=URL(fileURLWithPath:CommandLine.arguments[2])
let original=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:Data(contentsOf:sourceURL))
let acceptedClearance=original.foundationCheckpoint()["acceptedMinimumClearance"] as? Double
var checks:[[String:Any]]=[]
alarm(30)
for run in 0..<2 {
    let file=root.appendingPathComponent("checkpoint-\(run).json")
    let candidate=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:Data(contentsOf:file))
    var state=candidate.state
    var refresh:String?=nil
    do{try RopePassageTopology.refresh(state:&state,input:input)}catch{refresh=String(describing:error)}
    let start=ProcessInfo.processInfo.systemUptime
    let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[original.state.boardHeight,state.boardHeight])
    let measureSeconds=ProcessInfo.processInfo.systemUptime-start
    let old=original.state
    let angle=2*acos(min(1,abs(simd_dot(old.orientation.vector,state.orientation.vector))))
    var sweptWood:[Int]=[],selfSweeps=true,interSweeps=true
    let sweptStart=ProcessInfo.processInfo.systemUptime
    for r in state.ropes.indices {
        let rope=state.ropes[r]
        for i in rope.restLengths.indices {
            let a=old.boardPoint(old.ropes[r].positions[i]),b=old.boardPoint(old.ropes[r].positions[i+1])
            let nextA=state.boardPoint(rope.positions[i]),nextB=state.boardPoint(rope.positions[i+1])
            func deviation(_ j:Int)->Double{
                if rope.attachments[j] != nil{return 0}
                return RopeMotionSweep.rotationalDeviation(start:old.ropes[r].positions[j]-SIMD3(0,old.boardHeight,0),end:rope.positions[j]-SIMD3(0,state.boardHeight,0),angle:angle)
            }
            let curve=max(deviation(i),deviation(i+1)),radius=rope.radius-0.00005
            let movement=max(simd_distance(a,nextA),simd_distance(b,nextB))
            let clearance=acceptedClearance ?? collider.segmentClearance(from:a,to:b)
            if movement+curve<=clearance-radius{continue}
            if collider.sweptSegmentContact(previousStart:a,previousEnd:b,start:nextA,end:nextB,radius:radius+curve) != nil{sweptWood.append(i)}
        }
        selfSweeps = selfSweeps && RopeMotionSweep.selfContactValid(previous:old.ropes[r].positions,positions:rope.positions,radius:rope.radius,supports:rope.supports,restLengths:rope.restLengths)
    }
    for a in state.ropes.indices {for b in state.ropes.indices where b>a{
        interSweeps = interSweeps && RopeCordContacts.sweepValid(previousFirst:old.ropes[a],first:state.ropes[a],previousSecond:old.ropes[b],second:state.ropes[b])
    }}
    let sweepSeconds=ProcessInfo.processInfo.systemUptime-sweptStart
    // Test actual unaveraged stock capsules separately against the original mesh.
    let capsules=try decodeCheckpointJSON(Data(contentsOf:root.appendingPathComponent("capsules-\(run).json")))
    var capsuleClearance=Double.infinity
    for rope in capsules["ropes"] as! [[String:Any]] {for l in rope["capsules"] as! [[String:[Double]]]{
        func p(_ a:[Double])->SIMD3<Double>{SIMD3(a[0],a[1],a[2])}
        capsuleClearance=min(capsuleClearance,collider.segmentClearance(from:state.boardPoint(p(l["a"]!)),to:state.boardPoint(p(l["b"]!))))
    }}
    checks.append(["run":run,"geometryAccepted":metrics.geometryAccepted && refresh==nil,
        "lengthError":metrics.totalLengthError,"strain":metrics.maximumLocalStrain,"clearance":metrics.minimumSegmentClearance,
        "actualCapsuleClearance":capsuleClearance,"topology":metrics.topologyValid,"topologyFailure":metrics.topologyFailure as Any? ?? NSNull(),
        "refreshFailure":refresh as Any? ?? NSNull(),"woodSweepFailures":sweptWood,"selfSweepValid":selfSweeps,"interSweepValid":interSweeps,
        "metricsSeconds":measureSeconds,"sweepSeconds":sweepSeconds,"boardHeight":state.boardHeight,
        "boardDelta":state.boardHeight-old.boardHeight,"boardVerticalVelocity":state.boardVerticalVelocity])
}
alarm(0)
let outputName=CommandLine.arguments.count>4 ? CommandLine.arguments[4]:"physical-checks.json"
guard !outputName.contains("/"),!outputName.contains("..") else{throw RopePhysicsError.invalid("Invalid verifier output name")}
try JSONSerialization.data(withJSONObject:["checks":checks],options:[.sortedKeys,.prettyPrinted]).write(to:root.appendingPathComponent(outputName))
print("Original physical verifier completed")
