import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
let upright=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
let seed=try RopeThreadedSeed.make(input:input,profileID:input.profiles[0].id,orientation:upright,collider:collider)
var solver=try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
var records:[[String:Any]]=[]
func serialize(_ x:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:x,options:[.sortedKeys])}
func persist(_ failure:String?)throws {
    var result:[String:Any]=["owner":"strong-owl-live-physics","instrumentationOnly":true,"adopted":false,
        "dt":1.0/240,"completed":records.count==540,"steps":records]
    if let failure {result["failure"]=failure}
    try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
}
do {
    for step in 1...540 {
        let target=simd_quatd(angle:step<=240 ? Double.pi/6:0,axis:SIMD3<Double>(0,0,1))
        var control=solver
        ContactCycleTrace.enabled=false;alarm(10)
        let original=try control.step(dt:1.0/240,targetOrientation:target)
        ContactCycleTrace.corrections=[];ContactCycleTrace.enabled=true
        let observed=try solver.step(dt:1.0/240,targetOrientation:target)
        ContactCycleTrace.enabled=false;alarm(0)
        guard try serialize(control.bundleCheckpoint())==serialize(solver.bundleCheckpoint()),
              control.reviewStepCorrections==solver.reviewStepCorrections,
              control.reviewStepCaps==solver.reviewStepCaps,control.reviewStepRetries==solver.reviewStepRetries,
              original.settled==observed.settled else {throw RopePhysicsError.invalid("observer changed state/decisions at step \(step)")}
        guard observed.metrics.geometryAccepted else {throw RopePhysicsError.invalid("physical failure at step \(step)")}
        records.append(["step":step,"corrections":ContactCycleTrace.corrections,
            "QPs":solver.reviewStepCorrections,"caps":solver.reviewStepCaps,"retries":solver.reviewStepRetries,
            "settled":observed.settled,"bitIdentity":true])
        if step<=4 || step%20==0 {print("census step",step,"QPs",solver.reviewStepCorrections);fflush(stdout)}
    }
    try persist(nil)
    print("PASS 540-step observer identity; no speed claim")
} catch {try persist(String(describing:error));print("FAIL",error);exit(2)}
