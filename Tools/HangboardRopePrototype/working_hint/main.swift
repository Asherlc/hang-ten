import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1]),checkpoint=URL(fileURLWithPath:CommandLine.arguments[2])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String),collider=try RopeTriangleCollider(input:input)
var propagated=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:Data(contentsOf:checkpoint))
func serialize(_ x:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys])}
let target=simd_quatd(angle:Double.pi/2,axis:SIMD3<Double>(0,0,1))
var reports:[[String:Any]]=[]
for step in 1...20 {
 var c=try ColdRopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:serialize(propagated.foundationCheckpoint()))
 var w=propagated
 alarm(10)
 let coldStart=ProcessInfo.processInfo.systemUptime;_ = try c.step(dt:1.0/240,targetOrientation:target)
 let coldTime=ProcessInfo.processInfo.systemUptime-coldStart
 let start=ProcessInfo.processInfo.systemUptime;_ = try w.step(dt:1.0/240,targetOrientation:target)
 let elapsed=ProcessInfo.processInfo.systemUptime-start
 alarm(0)
 var difference=abs(c.state.boardHeight-w.state.boardHeight)
 for r in w.state.ropes.indices {for i in w.state.ropes[r].positions.indices {difference=max(difference,simd_distance(w.state.ropes[r].positions[i],c.state.ropes[r].positions[i]))}}
 guard difference<=0.000001 else {throw RopePhysicsError.invalid("working hint difference \(difference) at \(step)")}
 guard let cache=w.sweepCacheIdentity() else {throw RopePhysicsError.invalid("missing sweep cache")}
 for r in w.state.ropes.indices {for i in w.state.ropes[r].restLengths.indices {
  let a=w.state.boardPoint(w.state.ropes[r].positions[i]),b=w.state.boardPoint(w.state.ropes[r].positions[i+1])
  guard cache[r][i]==collider.segmentClearance(from:a,to:b).bitPattern else {throw RopePhysicsError.invalid("cache is not exact accepted clearance")}
 }}
 let physical=try serialize(w.foundationCheckpoint())
 do {_ = try w.step(dt:0,targetOrientation:target);throw RopePhysicsError.invalid("bad dt accepted")} catch {
  guard try physical==serialize(w.foundationCheckpoint()),w.sweepCacheIdentity()==cache else {throw RopePhysicsError.invalid("cache rollback")}
 }
 reports.append(["step":step,"controlSeconds":coldTime,"candidateSeconds":elapsed,"differenceMeters":difference,"exactCache":true])
 propagated=w
 print("step",step,"control",coldTime,"candidate",elapsed);fflush(stdout)
}
try JSONSerialization.data(withJSONObject:["owner":"strong-owl-live-physics","steps":reports,"passed":true,"rollback":true],options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
print("PASS20pairedsame-state steps within 1 micrometre, original and independent accepted perlink clearances bit-identical")
