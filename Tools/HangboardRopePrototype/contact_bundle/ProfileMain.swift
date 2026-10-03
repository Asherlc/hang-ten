import Foundation
import simd
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1]),checkpoint=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]))
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String),collider=try RopeTriangleCollider(input:input)
let target=simd_quatd(angle:Double.pi/6,axis:SIMD3<Double>(0,0,1))
var initial=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint)
initial.setBundleExperiment(true)
let original=try ControlRopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint)
func serialize(_ value:[String:Any])throws->Data {try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys])}
var unprofiled=initial,unprofiledOriginal=original
alarm(10);_ = try unprofiled.step(dt:1.0/240,targetOrientation:target);_ = try unprofiledOriginal.step(dt:1.0/240,targetOrientation:target);alarm(0)
var records:[String:[String:Any]]=[:]
func runCandidate()throws {
    var x=initial
    RopeBundleCensus.reset();RopeBundleCensus.enabled=true;AcceptedSolverProfile.enabled=true
    let start=ProcessInfo.processInfo.systemUptime
    _ = try x.step(dt:1.0/240,targetOrientation:target)
    let elapsed=ProcessInfo.processInfo.systemUptime-start
    AcceptedSolverProfile.enabled=false;RopeBundleCensus.enabled=false
    guard try serialize(x.bundleCheckpoint())==serialize(unprofiled.bundleCheckpoint()),
        try serialize(x.bundleReport)==serialize(unprofiled.bundleReport),x.reviewStepCorrections==unprofiled.reviewStepCorrections,
        x.reviewStepCaps==unprofiled.reviewStepCaps,x.reviewStepRetries==unprofiled.reviewStepRetries else {throw RopePhysicsError.invalid("profile changed candidate result/decisions")}
    records["candidate"]=["seconds":elapsed,"buckets":AcceptedSolverProfile.output(),"events":RopeBundleCensus.events,
        "distinctGeometryKeys":RopeBundleCensus.keys.count,"QPs":x.reviewStepCorrections,"bundle":x.bundleReport,"bitIdentity":true]
}
func runOriginal()throws {
    var x=original
    RopeBundleCensus.reset();RopeBundleCensus.enabled=true;AcceptedSolverProfile.enabled=true
    let start=ProcessInfo.processInfo.systemUptime
    _ = try x.step(dt:1.0/240,targetOrientation:target)
    let elapsed=ProcessInfo.processInfo.systemUptime-start
    AcceptedSolverProfile.enabled=false;RopeBundleCensus.enabled=false
    guard try serialize(x.bundleCheckpoint())==serialize(unprofiledOriginal.bundleCheckpoint()),x.reviewStepCorrections==unprofiledOriginal.reviewStepCorrections,
        x.reviewStepCaps==unprofiledOriginal.reviewStepCaps,x.reviewStepRetries==unprofiledOriginal.reviewStepRetries else {throw RopePhysicsError.invalid("profile changed original result")}
    records["original"]=["seconds":elapsed,"buckets":AcceptedSolverProfile.output(),"events":RopeBundleCensus.events,
        "distinctGeometryKeys":RopeBundleCensus.keys.count,"QPs":x.reviewStepCorrections,"bitIdentity":true]
}
do {
    alarm(10);try runOriginal();try runCandidate();alarm(0)
    let result:[String:Any]=["owner":"strong-owl-live-physics","records":records,"adopted":false,"instrumentationOnly":true,
        "scope":"one fixed native step, original and failed bundle; unchanged arithmetic/decisions; not a performance acceptance rerun"]
    try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("profile.json"))
    print("PASS instrumentation bit identity",records)
} catch {print("FAIL reuse census",error);exit(2)}
