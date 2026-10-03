import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let checkpoint=URL(fileURLWithPath:CommandLine.arguments[2])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
let upright=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
let profile=input.profiles[0]
let seed=try RopeThreadedSeed.make(input:input,profileID:profile.id,orientation:upright,collider:collider)
var solver=try RopeDynamicsSolver.prepareDisplay(input:input,state:seed,collider:collider).solver
let initial=solver.state
var reports:[[String:Any]]=[]
var phaseSettled=[false,false]
func serialize(_ x:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys])}
func metrics(_ m:RopeSimulationMetrics)->[String:Any] {
 ["geometryAccepted":m.geometryAccepted,"strain":m.maximumLocalStrain,"lengthError":m.totalLengthError,
  "clearance":m.minimumSegmentClearance,"clearanceMargin":m.minimumClearanceMargin,"topology":m.topologyValid,
  "speed":m.maximumSpeed,"displacement":m.boardDisplacement]
}
func persist(_ failure:String?)throws {
 var result:[String:Any]=["owner":"strong-owl-live-physics","steps":reports,"completed":reports.count==540,
   "movementStopMeters":0.00005,"strainStop":0.0002,"dt":1.0/240,"phaseSettled":phaseSettled,"adopted":false]
 if let failure {result["failure"]=failure}
 try serialize(result).write(to:root.appendingPathComponent("result.json"))
}
do {
 for step in 1...540 {
  let phase=step<=240 ? 0:1
  let target=simd_quatd(angle:phase==0 ? Double.pi/6:0,axis:SIMD3<Double>(0,0,1))
  let paired=step<=4 || step%20==0
  let before=try serialize(solver.foundationCheckpoint())
  var reference:ColdRopeDynamicsSolver?
  if paired {reference=try ColdRopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:before)}
  var coldResult:[String:Any]=[:]
  func control()throws {
   guard reference != nil else{return}
   ConvergenceTrace.reset(threshold:1e-8);alarm(10)
   let start=ProcessInfo.processInfo.systemUptime
   let frame=try reference!.step(dt:1.0/240,targetOrientation:target)
   let elapsed=ProcessInfo.processInfo.systemUptime-start
   alarm(0)
   coldResult=["seconds":elapsed,"trace":ConvergenceTrace.result(),"metrics":metrics(frame.metrics)]
  }
  if step%40 != 0 {try control()}
  ConvergenceTrace.reset(threshold:0.00005);alarm(10)
  let start=ProcessInfo.processInfo.systemUptime
  let frame=try solver.step(dt:1.0/240,targetOrientation:target)
  let elapsed=ProcessInfo.processInfo.systemUptime-start
  alarm(0)
  let trace=ConvergenceTrace.result(),retries=ConvergenceTrace.retries
  let capped=ConvergenceTrace.capped
  if step%40==0 {try control()}
  guard frame.metrics.geometryAccepted else {throw RopePhysicsError.invalid("physical metrics at \(step)")}
  for r in solver.state.ropes.indices {
   let a=initial.ropes[r],b=solver.state.ropes[r]
   guard a.id==b.id,a.radius==b.radius,a.linearMass==b.linearMass,a.restLengths==b.restLengths,
     a.supports==b.supports,a.attachments==b.attachments,a.portals==b.portals,a.channelSegments==b.channelSegments else {
    throw RopePhysicsError.invalid("material/bindings changed")
   }
  }
  var report:[String:Any]=["step":step,"phase":phase,"seconds":elapsed,"trace":trace,"metrics":metrics(frame.metrics),
    "settled":frame.settled,"height":frame.boardHeight,"orientation":Array(frame.orientation.vector.indices).map{frame.orientation.vector[$0]}]
  if let reference {
   var difference=abs(solver.state.boardHeight-reference.state.boardHeight)
   for r in solver.state.ropes.indices {for i in solver.state.ropes[r].positions.indices {
    difference=max(difference,simd_distance(solver.state.ropes[r].positions[i],reference.state.ropes[r].positions[i]))
   }}
   let t=coldResult["trace"] as! [String:Any]
   let coldCapped=t["capped"] as! Bool,coldRetries=t["retries"] as! Int
   report["reference"]=coldResult;report["sameInputDifferenceMeters"]=difference
   report["referenceConverged"] = !coldCapped
   reports.append(report)
   guard !(capped && !coldCapped),retries<=coldRetries else {throw RopePhysicsError.invalid("new cap/retry at \(step)")}
   if !coldCapped && difference>0.00005 {throw RopePhysicsError.invalid("converged reference difference \(difference) at \(step)")}
  } else {reports.append(report)}
  phaseSettled[phase]=phaseSettled[phase] || frame.settled
  try persist(nil)
  if step<=4 || step%20==0 {print("step",step,"seconds",elapsed,"corrections",(trace["corrections"] as! [[String:Double]]).count,"cap",capped,"settled",frame.settled);fflush(stdout)}
 }
 for phase in 0...1 {
  let tail=reports.filter{($0["phase"] as! Int)==phase}.suffix(60)
  guard tail.allSatisfy({ report in let m=report["metrics"] as! [String:Any];return (m["speed"] as! Double)<0.001 && (m["displacement"] as! Double)<0.0001}) else {throw RopePhysicsError.invalid("sustained settling phase \(phase)")}
 }
 guard phaseSettled.allSatisfy({$0}) else {throw RopePhysicsError.invalid("turn/return did not settle")}
 try serialize(solver.foundationCheckpoint()).write(to:root.appendingPathComponent("after.json"))
 try persist(nil)
 print("PASS fixed physical turn/return; performance requires independent distribution check")
} catch {
 try persist(String(describing:error));print("FAIL",error);fflush(stdout);exit(2)
}
