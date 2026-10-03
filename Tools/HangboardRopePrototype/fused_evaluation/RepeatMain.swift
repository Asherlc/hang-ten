import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let checkpoint=URL(fileURLWithPath:CommandLine.arguments[2]),prior=URL(fileURLWithPath:CommandLine.arguments[3])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
let seed=try Data(contentsOf:checkpoint),expected=try Data(contentsOf:prior)
let original=try ColdRopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:seed)
let candidate=try RopeDynamicsSolver.restoreFoundation(input:input,collider:collider,data:seed)
let target=simd_quatd(angle:Double.pi/2,axis:SIMD3<Double>(0,0,1))
func serialize(_ x:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:x,options:[.sortedKeys,.prettyPrinted])}
var c=candidate,b=original
let initial=c.debugEvaluation(c.state)
guard c.debugEvaluation(c.state)==initial,EvaluationAudit.evaluations==1 else {throw RopePhysicsError.invalid("cache repeated key")}
var changed=c.state;changed.boardHeight += 0.000001
guard c.debugEvaluation(changed) != initial,EvaluationAudit.evaluations==2 else {throw RopePhysicsError.invalid("cache height key")}
changed=c.state;changed.orientation=simd_quatd(angle:0.0001,axis:SIMD3(0,0,1))*changed.orientation
guard c.debugEvaluation(changed) != initial,EvaluationAudit.evaluations==3 else {throw RopePhysicsError.invalid("cache orientation key")}
changed=c.state;changed.ropes[0].positions[92].x += 0.000001
guard c.debugEvaluation(changed) != initial,EvaluationAudit.evaluations==4 else {throw RopePhysicsError.invalid("cache position key")}
changed=c.state
let id=changed.ropes[0].portalCrossings.keys.sorted()[0],cross=changed.ropes[0].portalCrossings[id]!
changed.ropes[0].portalCrossings[id]=RopePortalCrossing(segment:cross.segment,fraction:cross.fraction+0.000001)
guard c.debugEvaluation(changed) != initial,EvaluationAudit.evaluations==5 else {throw RopePhysicsError.invalid("cache crossing key")}
let score1=try c.debugMerit(c.state,prediction:c.state,penalty:1)
guard try score1.bitPattern==b.debugMerit(b.state,prediction:b.state,penalty:1).bitPattern else {throw RopePhysicsError.invalid("merit original")}
var prediction=c.state;prediction.boardHeight += 0.00001;prediction.ropes[0].positions[50].x += 0.00001
let score2=try c.debugMerit(c.state,prediction:prediction,penalty:1)
guard try score2.bitPattern==b.debugMerit(b.state,prediction:prediction,penalty:1).bitPattern,score1.bitPattern != score2.bitPattern else {throw RopePhysicsError.invalid("changed prediction/stale score negative control")}
let computations=EvaluationAudit.merits
let score3=try c.debugMerit(c.state,prediction:prediction,penalty:2)
guard try score3.bitPattern==b.debugMerit(b.state,prediction:prediction,penalty:2).bitPattern,EvaluationAudit.merits==computations else {throw RopePhysicsError.invalid("penalty parts reuse")}
guard try c.debugWeightedMerit(c.state,prediction:prediction,factor:2).bitPattern==b.debugWeightedMerit(b.state,prediction:prediction,factor:2).bitPattern else {throw RopePhysicsError.invalid("weights cache invalidation")}
let cache=c.debugEvaluation(c.state),physical=try serialize(c.foundationCheckpoint())
do {_ = try c.step(dt:0,targetOrientation:target);throw RopePhysicsError.invalid("invalid step accepted")} catch {
 guard try serialize(c.foundationCheckpoint())==physical,c.debugEvaluation(c.state)==cache else {throw RopePhysicsError.invalid("cache transaction")}
}
var reports:[[String:Any]]=[]
for pair in 0..<7 {
 var cold=original,warm=candidate
 func control()throws->Double {alarm(10);let start=ProcessInfo.processInfo.systemUptime;_ = try cold.step(dt:1.0/240,targetOrientation:target);alarm(0);return ProcessInfo.processInfo.systemUptime-start}
 func fused()throws->Double {EvaluationAudit.reset();alarm(10);let start=ProcessInfo.processInfo.systemUptime;_ = try warm.step(dt:1.0/240,targetOrientation:target);alarm(0);return ProcessInfo.processInfo.systemUptime-start}
 let a:Double,d:Double
 if pair%2==0 {a=try control();d=try fused()} else {d=try fused();a=try control()}
 guard try serialize(cold.foundationCheckpoint())==expected,try serialize(warm.foundationCheckpoint())==expected,
       EvaluationAudit.evaluations==13,EvaluationAudit.merits==13 else {throw RopePhysicsError.invalid("pair state/count identity")}
 reports.append(["pair":pair,"controlSeconds":a,"fusedSeconds":d,"ratio":d/a,"configurations":EvaluationAudit.evaluations,"meritParts":EvaluationAudit.merits])
 print("pair",pair,"control",a,"fused",d);fflush(stdout)
}
let median=reports.map{$0["ratio"] as! Double}.sorted()[3]
try JSONSerialization.data(withJSONObject:["owner":"strong-owl-live-physics","pairs":reports,"medianPairedRatio":median,"passed":median<=0.70,"cacheInvalidation":true,"changedPredictionNegativeControl":true,"bitIdentity":true],options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("repeat.json"))
guard median<=0.70 else {throw RopePhysicsError.invalid("fixed repeat performance gate")}
print("PASS interleaved median",median,"cache guards and full-state identity")
