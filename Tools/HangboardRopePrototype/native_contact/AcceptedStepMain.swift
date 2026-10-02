import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let checkpointURL=URL(fileURLWithPath:CommandLine.arguments[2])
let priorControlURL=URL(fileURLWithPath:CommandLine.arguments[3])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
alarm(60)
let collider=try RopeTriangleCollider(input:input)
let original=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:Data(contentsOf:checkpointURL))
alarm(0)
var reports:[[String:Any]]=[]
let target=simd_quatd(angle:Double.pi/2,axis:SIMD3<Double>(0,0,1))
for run in 0..<2 {
    var solver=original
    AcceptedSolverProfile.buckets=[:];AcceptedSolverProfile.enabled=run==0
    alarm(10)
    let start=ProcessInfo.processInfo.systemUptime
    let frame=try solver.step(dt:1.0/240,targetOrientation:target)
    let elapsed=ProcessInfo.processInfo.systemUptime-start
    alarm(0)
    guard elapsed<=1,frame.metrics.geometryAccepted else {throw RopePhysicsError.invalid("Accepted profile work/geometry gate failed")}
    let output=try JSONSerialization.data(withJSONObject:solver.foundationCheckpoint(),options:[.sortedKeys,.prettyPrinted])
    try output.write(to:root.appendingPathComponent("after-\(run).json"))
    reports.append(["run":run,"profiled":run==0,"seconds":elapsed,"buckets":AcceptedSolverProfile.output(),
        "strain":frame.metrics.maximumLocalStrain,"lengthError":frame.metrics.totalLengthError,
        "clearance":frame.metrics.minimumSegmentClearance,"topology":frame.metrics.topologyValid])
    print("run",run,"seconds",elapsed,"accepted",frame.metrics.geometryAccepted);fflush(stdout)
}
let a=try Data(contentsOf:root.appendingPathComponent("after-0.json"))
let b=try Data(contentsOf:root.appendingPathComponent("after-1.json"))
let prior=try Data(contentsOf:priorControlURL)
guard a==b,a==prior else {throw RopePhysicsError.invalid("Instrumentation changed accepted whole state")}
try JSONSerialization.data(withJSONObject:["scope":"single accepted original solver cost discriminator; host only",
 "wholeStateBitIdentity":true,"matchesPriorAcceptedControl":true,"reports":reports],options:[.sortedKeys,.prettyPrinted])
 .write(to:root.appendingPathComponent("report.json"))
print("PASS whole-state bit identity against same-binary control and prior accepted output")
