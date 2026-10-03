"""Deliberate guarded revisit of all-phase full-QP norm termination."""
from armijo.snapshot import once

def solver_source(source):
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var arrivalStopExperiment=false')
    source=once(source,'let limit=convergenceExperiment ? (arrivedNow ? 0.001*dt:0.00005):1e-8',
        'let limit=convergenceExperiment ? (arrivalStopExperiment ? 0.00005:(arrivedNow ? 0.001*dt:0.00005)):1e-8')
    return source

def driver_source(source,checkpoint=109):
    source=source.replace('candidate.armijoExperiment=true','candidate.arrivalStopExperiment=true').replace('b.armijoExperiment=true','b.arrivalStopExperiment=true')
    source=once(source,'var pairs:[[String:Any]]=[]','var pairs:[[String:Any]]=[]\nvar lastFrame:RopeFrameSnapshot?=nil')
    source=once(source,'    _ = try x.step(dt:1.0/240,targetOrientation:target)','    lastFrame = try x.step(dt:1.0/240,targetOrientation:target)')
    source=once(source,'    result["candidateMetrics"]=try check(candidate)','    result["candidateMetrics"]=try check(candidate)\n    result["candidateCaps"]=candidate.reviewStepCaps;result["candidateRetries"]=candidate.reviewStepRetries\n    result["candidateSeconds"]=probe.0;result["controlSeconds"]=control.0\n    result["candidateSettled"]=lastFrame!.settled\n    if lastFrame!.settled {\n        var continuation=try RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:serialize(candidate.bundleCheckpoint()),strict:true)\n        _ = try run(&continuation)\n        let frame=lastFrame!\n        result["strictContinuation"]=["settled":frame.settled,"speed":frame.metrics.maximumSpeed,\n            "boardDisplacement":frame.metrics.boardDisplacement,"caps":continuation.reviewStepCaps,"retries":continuation.reviewStepRetries]\n        try persist(nil)\n        guard frame.settled,continuation.reviewStepCaps==0,continuation.reviewStepRetries==0 else {\n            throw RopePhysicsError.invalid("strict false-settle continuation")\n        }\n    }')
    source=once(source,'guard candidate.reviewStepCaps<=original.reviewStepCaps,candidate.reviewStepRetries<=original.reviewStepRetries,','guard candidate.reviewStepCaps==0,candidate.reviewStepRetries==0,original.reviewStepCaps==0,original.reviewStepRetries==0,')
    source=once(source,'    guard candidate.reviewStepCorrections<=5 else','    try persist(nil)\n    guard candidate.reviewStepCorrections<=5 else')
    source=once(source,'"sigma":RopeArmijo.sigma,"step":109]','"guardedArrivalStop":true,"step":109]')
    if checkpoint==140:
        source=once(source,'for step in 1...108','for step in 1...139')
        source=once(source,'result["prefixIdentitySteps"]=108','result["prefixIdentitySteps"]=139')
        source=once(source,'candidate.reviewStepCorrections<=5','candidate.reviewStepCorrections<=2')
        source=source.replace('fixed <=5-QP work gate','fixed <=2-QP ordinary-step work gate')
        source=once(source,'"step":109]','"step":140]')
        source=once(source,'guard median<=0.80','guard median<=1.10')
        source=source.replace('fixed median <=0.80 speed gate','fixed median <=1.10 ordinary-step overhead gate')
        source=source.replace('isolated step109','isolated step140')
    return source

def trajectory_source(source):
    source=once(source,'var control=initial,candidate=initial,records:[[String:Any]]=[]','var control=initial,candidate=initial,records:[[String:Any]]=[]\ncandidate.arrivalStopExperiment=true')
    source=once(source,'        if hz==240 {','        if hz==240 && !candidate.arrivalStopExperiment {')
    source=once(source,'if !preflight,measured.2.settled,!settledPhases.contains(phase) {','if !preflight,measured.2.settled {')
    source=once(source,'"controlHz":240,"preflight":preflight,"armijoEnabled":false]','"controlHz":240,"preflight":preflight,"armijoEnabled":false,"guardedArrivalStop":true]')
    return source
