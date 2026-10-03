// Current all-contact control from the reviewable plan executes before this.
func require(_ value:Bool,_ message:String) throws {
    guard value else {throw RopePhysicsError.invalid(message)}
}
do {
    let repaired=try RopeContactBundle.solveTranslatedCapsule(collider:collider,from:a,to:b,radius:radius,
        factor:factor,base:[-0.0002,-0.0002],border:[0])
    let repairedClearance=clearance(repaired.base,repaired.height)
    try require(repairedClearance>=radius-0.00005,"Missing second-wall repair: actual mesh clearance \(repairedClearance)")
    try require((2...4).contains(repaired.passes),"Corner did not require bounded fresh coupled repairs")
    try require(repaired.height<0 && repaired.base[1]<repaired.base[0],"Board-height coupling was lost")
    let fartherA=SIMD3<Double>(0.005,0.00355,-0.005),fartherB=SIMD3<Double>(0.005,0.00355,0.005)
    let farther=try RopeContactBundle.solveTranslatedCapsule(collider:collider,from:fartherA,to:fartherB,radius:radius,
        factor:factor,base:[-0.002,-0.0002],border:[0])
    let delta=SIMD3(farther.base[0],farther.base[1]-farther.height,0)
    let fartherClearance=collider.segmentClearance(from:fartherA+delta,to:fartherB+delta)
    try require(fartherClearance>=radius-0.00005,"Trial blocker vanished outside current discovery cutoff")
    try require((2...4).contains(farther.passes),"Distant blocker repair work changed")
    // A known global winner must not conceal a tied omitted wall.
    let omitted=collider.blockingFeatures(from:a,to:b,radius:0.0036,excluding:[6,7])
    try require(omitted.contains{$0.contact.normal.y>0.999},"Known/tied winner masked an omitted normal")
    // The same triangle is reevaluated after material motion; it cannot carry
    // its old fraction as a pin. Face6 is the x=0 right-face lower triangle.
    let switchedStart=SIMD3<Double>(0.00355,0.00355,0.01),switchedEnd=SIMD3<Double>(0.00355,0.00355,-0.01)
    let oldWitness=collider.contactForFeature(6,from:switchedStart,to:switchedEnd,radius:rowRadius)
    let slide=SIMD3<Double>(0,0,-0.02)
    let newWitness=collider.contactForFeature(6,from:switchedStart+slide,to:switchedEnd+slide,radius:rowRadius)
    try require(oldWitness.contact.fraction==1 && newWitness.contact.fraction==0,"Material fraction did not reevaluate after sliding")
    var insideFallback=false,sweepBlocked=false
    do {
        _ = try RopeContactBundle.solveTranslatedCapsule(collider:collider,from:a-SIMD3(0.006,0,0),to:b-SIMD3(0.006,0,0),
            radius:radius,factor:factor,base:[0,0],border:[0])
    } catch RopeContactBundle.Failure.insideFallback {insideFallback=true}
    try require(insideFallback,"Inside endpoints were reinterpreted as unsigned exterior clearance")
    do {
        _ = try RopeContactBundle.solveTranslatedCapsule(collider:collider,from:fartherA,to:fartherB,radius:radius,
            factor:factor,base:[-0.04,-0.0002],border:[0])
    } catch RopeContactBundle.Failure.sweptTraversal {sweepBlocked=true}
    try require(sweepBlocked,"Clear final endpoints bypassed whole-capsule wood CCD")
    let result:[String:Any]=["owner":"strong-owl-live-physics","cornerClearanceMeters":repairedClearance,
        "cornerPasses":repaired.passes,"fartherClearanceMeters":fartherClearance,"fartherPasses":farther.passes,
        "actualMeshChecksPassed":true,"insideRequiresOriginalFallback":insideFallback,"sweptTraversalRejected":sweepBlocked,
        "omittedTieDetected":true,"materialFractionReevaluated":true,
        "candidateAdopted":false,"scope":"translated capsule and shared height only; full rope integration pending"]
    try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:
        URL(fileURLWithPath:CommandLine.arguments[1]).appendingPathComponent("fixtures.json"))
    print("PASS repaired corner/distant blocker/tied omitted wall/sliding fraction/inside fallback/whole-capsule CCD fixtures")
} catch {
    print("FAIL contact bundle fixture",error);exit(2)
}
