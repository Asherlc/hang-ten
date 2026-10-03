func contactBits(_ outputs:[[RopeSegmentContact]])->[UInt64] {
    var bits:[UInt64]=[UInt64(outputs.count)]
    for hits in outputs {
        bits.append(UInt64(hits.count))
        for hit in hits {
            for point in [hit.centerlinePoint,hit.surfacePoint,hit.normal] {bits += [point.x.bitPattern,point.y.bitPattern,point.z.bitPattern]}
            bits += [hit.fraction.bitPattern,hit.penetrationDepth.bitPattern]
        }
    }
    return bits
}
func planarRowFixtures()throws {
    try planarRegionFixtures();try clippedPlanarFixtures()
    let path=".context/strong-owl-live-physics-coplanar-query-5a12d1ee2-chronological-corpus/native/result.json"
    let corpus=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:path))) as! [String:Any]
    var changed=0,checked=0
    for step in corpus["steps"] as! [[String:Any]] where [1,6,109,140,493].contains(step["step"] as! Int) {
        for q in (step["census"] as! [String:Any])["examples"] as! [[String:Any]] {
            let a=q["start"] as! [Double],b=q["end"] as! [Double],points=[SIMD3(a[0],a[1],a[2]),SIMD3(b[0],b[1],b[2])]
            let original=collider.fusedChainContacts(points:points,rowRadius:(0.0035+0.0001)+0.00005,meritRadius:0.0035+0.0001)
            let candidate=collider.fusedChainContacts(points:points,rowRadius:(0.0035+0.0001)+0.00005,meritRadius:0.0035+0.0001,planarPatchRows:true)
            let oldReceipts=original.clearances.map{$0?.bitPattern},newReceipts=candidate.clearances.map{$0?.bitPattern}
            guard contactBits(original.merits)==contactBits(candidate.merits),
                oldReceipts==newReceipts else {
                throw RopePhysicsError.invalid("row-only original full merit/receipt bit identity")
            }
            if contactBits(original.rows) != contactBits(candidate.rows) || contactBits(original.points) != contactBits(candidate.points) {changed += 1}
            checked += 1
        }
    }
    guard changed>0 else {throw RopePhysicsError.invalid("patch QP row routing must consume candidate outputs")}
    result["fixtureChangedQueries"]=changed;result["fixtureCheckedQueries"]=checked;result["meritReceiptBitsPreserved"]=true
    print("PASS QP patch row routing",changed,"of",checked,"original merit/receipts identical")
}
func signatures(_ rows:[[String:Any]])throws->Set<String> {
    try Set(rows.map {row in
        var signature=row;signature.removeValue(forKey:"row");signature.removeValue(forKey:"multiplier")
        return String(data:try serialize(signature),encoding:.utf8)!
    })
}
do {
    result=["owner":"strong-owl-live-physics","adopted":false,"step":109,"scope":"planar QP row nonlinear work-count discriminator; original triangle merit/receipts; no speed claim"]
    try planarRowFixtures();result["fixturesPass"]=true
    if CommandLine.arguments.contains("--fixtures-only") {try persist(nil);exit(0)}
    for step in 1...108 {
        let trace=try run(&initial).1
        let retained=(priorSteps[step-1]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]
        guard trace.count==retained.count else {throw RopePhysicsError.invalid("original prefix count identity")}
        for (a,b) in zip(trace,retained) {for key in ["alpha","movement","strain"] {
            guard (a[key] as! Double)==b[key] else {throw RopePhysicsError.invalid("original prefix numeric identity")}
        }}
    }
    result["prefixIdentitySteps"]=108
    let checkpoint=try serialize(initial.bundleCheckpoint());try checkpoint.write(to:root.appendingPathComponent("input.json"))
    var original=initial,candidate=initial;candidate.planarPatchRowsExperiment=true
    ArmijoTrace.collectPlanarBindings=true
    let control=try run(&original),probe=try run(&candidate)
    result["originalTrace"]=control.1;result["candidateTrace"]=probe.1
    result["originalQPs"]=original.reviewStepCorrections;result["candidateQPs"]=candidate.reviewStepCorrections
    result["originalCaps"]=original.reviewStepCaps;result["candidateCaps"]=candidate.reviewStepCaps
    result["originalRetries"]=original.reviewStepRetries;result["candidateRetries"]=candidate.reviewStepRetries
    result["currentDifferenceMeters"]=difference(original,candidate);result["candidateMetrics"]=try check(candidate)
    let a=try signatures(control.1.first!["initialWoodRows"] as! [[String:Any]])
    let b=try signatures(probe.1.first!["initialWoodRows"] as! [[String:Any]])
    result["initialWoodRowsOriginal"]=a.count;result["initialWoodRowsCandidate"]=b.count
    result["initialWoodRowsCommon"]=a.intersection(b).count;result["initialWoodRowsRemoved"]=a.subtracting(b).count;result["initialWoodRowsAdded"]=b.subtracting(a).count
    var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint,strict:true)
    let reference=try run(&strict)
    result["strictTrace"]=reference.1;result["strictDifferenceMeters"]=difference(strict,candidate)
    result["strictCaps"]=strict.reviewStepCaps;result["strictRetries"]=strict.reviewStepRetries
    try persist(nil)
    guard original.reviewStepCorrections==11,original.reviewStepCaps==0,original.reviewStepRetries==0,
        candidate.reviewStepCaps==0,candidate.reviewStepRetries==0,strict.reviewStepCaps==0,strict.reviewStepRetries==0,
        difference(original,candidate)<=0.00005,difference(strict,candidate)<=0.00005 else {
        throw RopePhysicsError.invalid("fixed planar row current/strict physical/cap/retry gate")
    }
    var rollback=candidate;let before=try serialize(rollback.bundleCheckpoint());var rejected=false
    do {_ = try rollback.step(dt:Double.nan,targetOrientation:target)}catch RopePhysicsError.invalid {rejected=true}
    guard rejected,rollback.planarPatchRowsExperiment,try serialize(rollback.bundleCheckpoint())==before else {
        throw RopePhysicsError.invalid("row mode/checkpoint rollback")
    }
    result["rollbackIdentity"]=true;result["accuracyPass"]=true;try persist(nil)
    guard candidate.reviewStepCorrections<=5 else {throw RopePhysicsError.invalid("fixed planar row <=5QP gate")}
    result["workScreenPass"]=true;try persist(nil)
    print("PASS planar QP row step109",candidate.reviewStepCorrections,"current",difference(original,candidate),"strict",difference(strict,candidate))
} catch {try persist(String(describing:error));print("FAIL planar QP row step109",error);exit(2)}
