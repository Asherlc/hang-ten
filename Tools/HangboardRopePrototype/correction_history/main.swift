import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let checkpoint=URL(fileURLWithPath:CommandLine.arguments[2]),prior=URL(fileURLWithPath:CommandLine.arguments[3])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
alarm(60)
let collider=try RopeTriangleCollider(input:input)
var propagated=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:Data(contentsOf:checkpoint))
alarm(0)
let target=simd_quatd(angle:Double.pi/2,axis:SIMD3<Double>(0,0,1))
var reports:[[String:Any]]=[]
func physical(_ s:RopeDynamicsSolver)throws->Data {try JSONSerialization.data(withJSONObject:s.foundationCheckpoint(),options:[.sortedKeys,.prettyPrinted])}
func difference(_ a:RopeDynamicsSolver,_ b:RopeDynamicsSolver)->Double {
 var d=abs(a.state.boardHeight-b.state.boardHeight)
 for r in a.state.ropes.indices {for i in a.state.ropes[r].positions.indices {
  d=max(d,simd_distance(a.state.ropes[r].positions[i],b.state.ropes[r].positions[i]))
 }}
 return d
}
func metrics(_ m:RopeSimulationMetrics)->[String:Any] {
 ["geometryAccepted":m.geometryAccepted,"strain":m.maximumLocalStrain,"lengthError":m.totalLengthError,
  "clearance":m.minimumSegmentClearance,"clearanceMargin":m.minimumClearanceMargin,"topology":m.topologyValid,"speed":m.maximumSpeed,"displacement":m.boardDisplacement]
}
func run(_ solver:inout RopeDynamicsSolver)throws->(RopeFrameSnapshot,Double,[String:Any]) {
 HistoryTrace.reset();alarm(10)
 let start=ProcessInfo.processInfo.systemUptime
 let frame=try solver.step(dt:1.0/240,targetOrientation:target)
 let elapsed=ProcessInfo.processInfo.systemUptime-start
 alarm(0)
 return (frame,elapsed,HistoryTrace.result())
}
func persist(_ failed:String?)throws {
 var report:[String:Any]=["owner":"strong-owl-live-physics","scope":"240 same-state paired host steps, unchanged physical model and convergence","steps":reports,"completed":reports.count==240]
 if let failed {report["failure"]=failed}
 try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys,.prettyPrinted]).write(to:root.appendingPathComponent("result.json"))
}
do {
 for step in 1...240 {
  var cold=propagated,warm=propagated;cold.clearCorrectionGuesses()
  let a:(RopeFrameSnapshot,Double,[String:Any]),b:(RopeFrameSnapshot,Double,[String:Any])
  if step%2==1 {a=try run(&cold);b=try run(&warm)} else {b=try run(&warm);a=try run(&cold)}
  let diff=difference(cold,warm)
  reports.append(["step":step,"coldSeconds":a.1,"warmSeconds":b.1,"coldTrace":a.2,"warmTrace":b.2,
   "coldMetrics":metrics(a.0.metrics),"warmMetrics":metrics(b.0.metrics),"maxDifferenceMeters":diff,"warmSettled":b.0.settled])
  guard diff<=0.000001,a.0.metrics.geometryAccepted,b.0.metrics.geometryAccepted else {throw RopePhysicsError.invalid("paired accuracy at step \(step), difference \(diff)")}
  if step==1 {
   guard try physical(warm)==Data(contentsOf:prior),warm.guessIdentity().count==1 else {throw RopePhysicsError.invalid("cold first step identity")}
   // Erasure and value-semantic rollback are substantive plumbing checks.
   let before=try physical(warm),history=warm.guessIdentity()
   do {_ = try warm.step(dt:0,targetOrientation:target);throw RopePhysicsError.invalid("invalid dt accepted")}
   catch {guard try physical(warm)==before,warm.guessIdentity()==history else {throw RopePhysicsError.invalid("rollback changed state/history")}}
   var altered=warm;altered.clearCorrectionGuesses()
   guard altered.guessIdentity().isEmpty,warm.guessIdentity()==history else {throw RopePhysicsError.invalid("history clearing mutates copy")}
   // A 2µm wrong result must be caught by the independently used comparator.
   var wrong=warm.foundationCheckpoint()
   wrong["boardHeight"]=(wrong["boardHeight"] as! Double)+0.000002
   let restored=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:JSONSerialization.data(withJSONObject:wrong))
   guard difference(warm,restored)>0.000001 else {throw RopePhysicsError.invalid("wrong solution negative control")}
  }
  let coldRetry=a.2["retries"] as! Int,warmRetry=b.2["retries"] as! Int
  guard !(warmRetry>0 && coldRetry==0) else {throw RopePhysicsError.invalid("warm-only retry at step \(step)")}
  propagated=warm
  try persist(nil)
  if step<=4 || step%20==0 {print("step",step,"cold",a.1,"warm",b.1,"corrections",(b.2["corrections"] as! [[String:Double]]).count,"difference",diff);fflush(stdout)}
 }
 try physical(propagated).write(to:root.appendingPathComponent("after.json"))
 print("completed240pairedsteps; evaluate registered distribution gates")
} catch {
 try persist(String(describing:error));print("FAIL",error);fflush(stdout);exit(2)
}
