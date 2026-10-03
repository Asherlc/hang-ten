func poseDifference(_ a:RopeSimulationState,_ b:RopeSimulationState)->Double {
    var maximum=abs(a.boardHeight-b.boardHeight)
    for r in a.ropes.indices {for i in a.ropes[r].positions.indices {
        maximum=max(maximum,simd_distance(a.ropes[r].positions[i],b.ropes[r].positions[i]))
    }}
    return maximum
}
do {
    result=["owner":"strong-owl-live-physics","adopted":false,"scope":"first held reaction stage, no integration or speed claim","step":3]
    try RopeLaggedReaction.fixtures();result["fixturesPass"]=true
    if CommandLine.arguments.contains("--fixtures-only") {try persist(nil);exit(0)}
    var original=initial
    var previousPrediction=initial.state
    for step in 1...2 {
        previousPrediction=original.laggedFreePrediction(dt:RopeLaggedReaction.h,targetOrientation:target)
        let trace=try run(&original).1
        let old=(priorSteps[step-1]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]
        guard trace.count==old.count,original.reviewStepCaps==0,original.reviewStepRetries==0 else {
            throw RopePhysicsError.invalid("cold original pair count/cap/retry identity")
        }
        for (a,b) in zip(trace,old) {for key in ["alpha","movement","strain"] {
            guard (a[key] as! Double)==b[key] else {throw RopePhysicsError.invalid("cold original pair numeric identity")}
        }}
    }
    result["prefixIdentitySteps"]=2
    let old=original.state,checkpoint=try serialize(original.bundleCheckpoint())
    try checkpoint.write(to:root.appendingPathComponent("input.json"))
    let free=original.laggedFreePrediction(dt:RopeLaggedReaction.h,targetOrientation:target)
    let proposed=try original.laggedProposal(previousPrediction:previousPrediction,previousSolved:old,targetOrientation:target)
    var control=original
    let controlTrace=try run(&control).1
    let retained=(priorSteps[2]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]
    guard controlTrace.count==retained.count else {throw RopePhysicsError.invalid("step3 control count identity")}
    for (a,b) in zip(controlTrace,retained) {for key in ["alpha","movement","strain"] {
        guard (a[key] as! Double)==b[key] else {throw RopePhysicsError.invalid("step3 control numeric identity")}
    }}
    var strict=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint,strict:true)
    result["strictTrace"]=try run(&strict).1;result["originalTrace"]=controlTrace
    let history=(original.foundationCheckpoint()["history"] as! [[Double]]).map{$0[1]}+[proposed.boardHeight]
    let metrics=try RopeSimulationMetrics.measure(state:proposed,input:input,collider:collider,boardHistory:history)
    var sweptWood=true,sweptSelf=true,sweptInterCord=true,immutable=true,reactionChange=abs((old.boardHeight-previousPrediction.boardHeight)-(control.state.boardHeight-free.boardHeight))
    for r in proposed.ropes.indices {
        sweptWood = collider.sweepChainIsClear(previous:old,next:proposed,rope:r,clearances:nil,
            globalClearance:original.foundationCheckpoint()["acceptedMinimumClearance"] as? Double) && sweptWood
        let a=old.ropes[r],b=proposed.ropes[r]
        sweptSelf = RopeMotionSweep.selfContactValid(previous:a.positions,positions:b.positions,radius:b.radius,
            supports:b.supports,restLengths:b.restLengths) && sweptSelf
        immutable = a.id==b.id && a.radius==b.radius && a.linearMass==b.linearMass && a.restLengths==b.restLengths &&
            a.supports==b.supports && a.attachments==b.attachments && a.portals==b.portals && a.channelSegments==b.channelSegments && immutable
        for i in b.positions.indices where b.supports[i]==nil && b.attachments[i]==nil {
            let held=old.ropes[r].positions[i]-previousPrediction.ropes[r].positions[i]
            let actual=control.state.ropes[r].positions[i]-free.ropes[r].positions[i]
            reactionChange=max(reactionChange,simd_length(held-actual))
        }
    }
    for a in proposed.ropes.indices {for b in proposed.ropes.indices where b>a {
        sweptInterCord = RopeCordContacts.sweepValid(previousFirst:old.ropes[a],first:proposed.ropes[a],
            previousSecond:old.ropes[b],second:proposed.ropes[b]) && sweptInterCord
    }}
    let currentDifference=poseDifference(control.state,proposed),strictDifference=poseDifference(strict.state,proposed)
    result["candidateMetrics"]=["geometryAccepted":metrics.geometryAccepted,"strain":metrics.maximumLocalStrain,
        "lengthError":metrics.totalLengthError,"clearanceMargin":metrics.minimumClearanceMargin,"speed":metrics.maximumSpeed,
        "topologyFailure":metrics.topologyFailure as Any? ?? NSNull()]
    result["sweptWood"]=sweptWood;result["sweptSelf"]=sweptSelf;result["sweptInterCord"]=sweptInterCord;result["immutable"]=immutable
    result["reactionChangeMeters"]=reactionChange;result["currentDifferenceMeters"]=currentDifference;result["strictDifferenceMeters"]=strictDifference
    let velocityDifference:Double=zip(control.state.ropes,proposed.ropes).map {a,b -> Double in zip(a.velocities,b.velocities).map{simd_distance($0,$1)}.max()!}.max()!
    result["maximumVelocityDifference"]=velocityDifference
    result["candidateQPs"]=0;result["controlQPs"]=control.reviewStepCorrections
    result["referenceCaps"]=control.reviewStepCaps+strict.reviewStepCaps;result["referenceRetries"]=control.reviewStepRetries+strict.reviewStepRetries
    try persist(nil)
    guard abs(currentDifference-reactionChange)<1e-14 else {throw RopePhysicsError.invalid("reaction change discriminator identity")}
    guard metrics.geometryAccepted,immutable,sweptWood,sweptSelf,sweptInterCord,currentDifference<=0.00005,strictDifference<=0.00005,
        control.reviewStepCaps==0,strict.reviewStepCaps==0,control.reviewStepRetries==0,strict.reviewStepRetries==0 else {
        throw RopePhysicsError.invalid("first held stage original physical/CCD/reference gate")
    }
    result["necessaryScreenPass"]=true;try persist(nil)
    print("PASS first held stage",currentDifference,"strict",strictDifference)
} catch {try persist(String(describing:error));print("FAIL first held stage",error);exit(2)}
