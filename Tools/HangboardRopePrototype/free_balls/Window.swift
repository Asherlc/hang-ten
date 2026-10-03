
struct FreeBallWindow {
    let final:RopeDynamicsSolver
    let records:[[String:Any]]
    let states:[RopeDynamicsSolver]
    let seconds:Double
    let qps:Int,skips:Int,conflicts:Int
    let beforeLast:Data
}
func window(_ seed:RopeDynamicsSolver,enabled:Bool,verify:Bool)throws->FreeBallWindow {
    var x=seed;x.clearanceBoundExperiment=enabled;x.freeBallExperiment=enabled;x.verifyFreeBallParity=verify
    guard x.freeBallAnchorSnapshot().isEmpty else {throw RopePhysicsError.invalid("window must start without anchors")}
    var records:[[String:Any]]=[],states:[RopeDynamicsSolver]=[],seconds=0.0,qps=0,skips=0,conflicts=0,beforeLast=Data()
    for step in 121...140 {
        if step==140 {beforeLast=try serialize(x.bundleCheckpoint())}
        let measurement=try run(&x)
        seconds += measurement.0;qps += x.reviewStepCorrections
        skips += x.freeBallCertifiedParities;conflicts += x.freeBallParityConflicts
        guard x.reviewStepCaps==0,x.reviewStepRetries==0 else {throw RopePhysicsError.invalid("window cap/retry")}
        records.append(["step":step,"seconds":measurement.0,"trace":measurement.1,"qps":x.reviewStepCorrections,
            "certifiedParities":x.freeBallCertifiedParities,"parityConflicts":x.freeBallParityConflicts,"metrics":try check(x)])
        states.append(x)
    }
    return FreeBallWindow(final:x,records:records,states:states,seconds:seconds,qps:qps,skips:skips,conflicts:conflicts,beforeLast:beforeLast)
}
func verifyDeterminism(_ a:FreeBallWindow,_ b:FreeBallWindow)throws {
    guard a.qps==b.qps,a.skips==b.skips,a.conflicts==b.conflicts else {throw RopePhysicsError.invalid("window count determinism")}
    for i in a.states.indices {
        guard try serialize(a.states[i].bundleCheckpoint())==serialize(b.states[i].bundleCheckpoint()),
            try serialize(["anchors":a.states[i].freeBallAnchorSnapshot()])==serialize(["anchors":b.states[i].freeBallAnchorSnapshot()]),
            try serialize(["trace":a.records[i]["trace"]!])==serialize(["trace":b.records[i]["trace"]!]) else {
            throw RopePhysicsError.invalid("window state/anchor/decision determinism")
        }
    }
}
do {
    try clearanceBoundFixtures();try freeBallFixtures()
    if CommandLine.arguments.contains("--fixtures-only") {print("PASS free-ball fixtures");exit(0)}
    for step in 1...120 {
        let record=try run(&initial).1
        let old=(priorSteps[step-1]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]
        guard record.count==old.count else {throw RopePhysicsError.invalid("prefix count identity")}
        for (a,b) in zip(record,old) {for key in ["movement","alpha","strain"] {
            guard (a[key] as! Double)==b[key] else {throw RopePhysicsError.invalid("prefix numeric identity")}
        }}
    }
    result["prefixDecisionIdentitySteps"]=120
    try serialize(initial.bundleCheckpoint()).write(to:root.appendingPathComponent("checkpoint.json"))
    let original=try window(initial,enabled:false,verify:false)
    let verified=try window(initial,enabled:true,verify:true)
    let candidate=try window(initial,enabled:true,verify:false)
    result["originalWindow"]=original.records;result["verifiedWindow"]=verified.records;result["candidateWindow"]=candidate.records
    result["certifiedParities"]=candidate.skips;result["verifiedParities"]=verified.skips;result["parityConflicts"]=verified.conflicts
    result["originalQPs"]=original.qps;result["candidateQPs"]=candidate.qps
    guard verified.conflicts==0,candidate.skips>0,candidate.qps<=original.qps else {throw RopePhysicsError.invalid("original parity oracle/work")}
    try verifyDeterminism(verified,candidate)
    let propagated=zip(original.states,candidate.states).map{difference($0,$1)}.max()!
    result["maximumPropagatedDifferenceMeters"]=propagated
    guard propagated<=0.00005 else {throw RopePhysicsError.invalid("propagated pose difference")}
    var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:candidate.beforeLast,strict:true)
    guard strict.freeBallAnchorSnapshot().isEmpty else {throw RopePhysicsError.invalid("restored anchor reset")}
    let strictMeasurement=try run(&strict)
    result["strictTrace"]=strictMeasurement.1;result["strictDifferenceMeters"]=difference(strict,candidate.final)
    guard strict.reviewStepCaps==0,strict.reviewStepRetries==0,difference(strict,candidate.final)<=0.00005 else {throw RopePhysicsError.invalid("strict reference")}
    var rollback=candidate.final
    let before=try serialize(["checkpoint":rollback.bundleCheckpoint(),"anchors":rollback.freeBallAnchorSnapshot()])
    var rejected=false
    do {_ = try rollback.step(dt:Double.nan,targetOrientation:target)}
    catch RopePhysicsError.invalid {rejected=true}
    guard rejected,try serialize(["checkpoint":rollback.bundleCheckpoint(),"anchors":rollback.freeBallAnchorSnapshot()])==before else {throw RopePhysicsError.invalid("anchor rollback")}
    result["invalidDtRollbackIdentity"]=true
    for iteration in 0..<7 {
        let a:FreeBallWindow,b:FreeBallWindow
        if iteration%2==0 {a=try window(initial,enabled:false,verify:false);b=try window(initial,enabled:true,verify:false)}
        else {b=try window(initial,enabled:true,verify:false);a=try window(initial,enabled:false,verify:false)}
        try verifyDeterminism(a,original);try verifyDeterminism(b,candidate)
        pairs.append(["originalSeconds":a.seconds,"candidateSeconds":b.seconds,"ratio":b.seconds/a.seconds])
    }
    result["workAndAccuracyPass"]=true
    let median=pairs.map{$0["ratio"] as! Double}.sorted()[3];result["medianRatio"]=median
    try persist(nil)
    guard median<=0.80 else {throw RopePhysicsError.invalid("fixed twenty-step median <=0.80 speed gate")}
    result["windowPass"]=true;try persist(nil)
    print("PASS free-ball window121-140; median",median,"skipped parity",candidate.skips,"QPs",candidate.qps)
} catch {try persist(String(describing:error));print("FAIL free-ball window",error);exit(2)}
