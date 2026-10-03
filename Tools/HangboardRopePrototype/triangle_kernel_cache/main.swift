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
func serialize(_ value:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys])}
func compare(_ x:RopeDynamicsSolver,_ y:ControlRopeDynamicsSolver) throws {
    guard try serialize(x.foundationCheckpoint())==serialize(y.foundationCheckpoint()),
          x.reviewStepCorrections==y.reviewStepCorrections,x.reviewStepCaps==y.reviewStepCaps,x.reviewStepRetries==y.reviewStepRetries else {
        throw RopePhysicsError.invalid("complete physical checkpoint or correction schedule changed")
    }
}
for step in 1...139 {
    alarm(10)
    _ = try candidate.step(dt:1.0/240,targetOrientation:target)
    _ = try control.step(dt:1.0/240,targetOrientation:target)
    alarm(0)
    try compare(candidate,control)
    if step%20==0 {print("prefix",step,"matched");fflush(stdout)}
}
var reports:[[String:Any]]=[]
for index in 0..<7 {
    var x=candidate,y=control
    var candidateSeconds=0.0,controlSeconds=0.0
    func measureCandidate() throws {
        let t=ProcessInfo.processInfo.systemUptime
        _ = try x.step(dt:1.0/240,targetOrientation:target)
        candidateSeconds=ProcessInfo.processInfo.systemUptime-t
    }
    func measureControl() throws {
        let t=ProcessInfo.processInfo.systemUptime
        _ = try y.step(dt:1.0/240,targetOrientation:target)
        controlSeconds=ProcessInfo.processInfo.systemUptime-t
    }
    alarm(10)
    if index%2==0 {try measureControl();try measureCandidate()} else {try measureCandidate();try measureControl()}
    alarm(0)
    try compare(x,y)
    guard x.reviewStepCorrections==2,x.reviewStepCaps==0,x.reviewStepRetries==0 else {throw RopePhysicsError.invalid("fixed two-QP discriminator changed")}
    reports.append(["run":index,"controlSeconds":controlSeconds,"candidateSeconds":candidateSeconds,"ratio":candidateSeconds/controlSeconds,"wholePhysicalCheckpointBitIdentity":true,"corrections":x.reviewStepCorrections])
    print("pair",index,controlSeconds,candidateSeconds);fflush(stdout)
}
let ratios=reports.map{$0["ratio"] as! Double}.sorted(),median=ratios[ratios.count/2]
let result:[String:Any]=["owner":"strong-owl-live-physics","prefixSteps":139,"pairedRuns":reports,"medianRatio":median,"fixedMaximumRatio":0.8,"accuracyPassed":true,"performancePassed":median<=0.8,"adopted":false,"scope":"complete native step 140 of fixed actual upright-to-30-degree trajectory, DEBUG convergence experiment, host-only"]
try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
print(median<=0.8 ? "PASS complete-step speed discriminator":"FAIL fixed complete-step speed discriminator",median)
if median>0.8 {exit(2)}
