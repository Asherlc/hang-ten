"""Early full-step strain stop, retaining original force test at actual quiet poses."""
from armijo.snapshot import once
from arrival_stop.snapshot import driver_source as arrival_driver,trajectory_source as arrival_trajectory

def solver_source(source):
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var quietStrainExperiment=false')
    source=once(source,'        let old=state','        let old=state\n        var expectedQuiet:Bool?=nil\n        if quietStrainExperiment {lastCorrectionFullStep=false}')
    source=once(source,'            if maximumStrain()<0.0002 && movement<limit && (!convergenceExperiment || !arrivedNow || lastCorrectionFullStep) {', '            let terminating:Bool\n            if quietStrainExperiment && convergenceExperiment {\n                let quiet=trialWouldSettle(previous:old,dt:dt,target:targetOrientation)\n                terminating=maximumStrain()<0.0002 && lastCorrectionFullStep && (!quiet || movement<0.001*dt)\n                if terminating {expectedQuiet=quiet}\n            } else {\n                terminating=maximumStrain()<0.0002 && movement<limit && (!convergenceExperiment || !arrivedNow || lastCorrectionFullStep)\n            }\n            if terminating {')
    source=once(source,'        let settled=arrived && time>=0.5 && metrics.maximumSpeed<0.001 && metrics.boardDisplacement<0.0001', '        let settled=arrived && time>=0.5 && metrics.maximumSpeed<0.001 && metrics.boardDisplacement<0.0001\n        if let expectedQuiet,expectedQuiet != settled {throw RopePhysicsError.invalid("trial quiet must equal final settled predicate")}')
    source+='\nextension RopeDynamicsSolver {\n    private func trialWouldSettle(previous:RopeSimulationState,dt:Double,target:simd_quatd)->Bool {\n        var speed=abs((state.boardHeight-previous.boardHeight)/dt)\n        for r in state.ropes.indices {for i in state.ropes[r].positions.indices {\n            let velocity=(state.ropes[r].positions[i]-previous.ropes[r].positions[i])/dt\n            speed=max(speed,simd_length(velocity))\n        }}\n        let prospectiveTime=time+dt\n        var prospectiveHistory=history\n        prospectiveHistory.append((prospectiveTime,state.boardHeight))\n        prospectiveHistory.removeAll{$0.0<prospectiveTime-0.5-dt/2}\n        let heights=prospectiveHistory.map{$0.1}\n        let displacement=(heights.max() ?? state.boardHeight)-(heights.min() ?? state.boardHeight)\n        let arrived=abs(simd_dot(state.orientation.vector,target.vector))>1-1e-12\n        return arrived && prospectiveTime>=0.5 && speed<0.001 && displacement<0.0001\n    }\n}\n'
    return source

def driver_source(source,checkpoint=109):
    source=arrival_driver(source,checkpoint).replace('arrivalStopExperiment','quietStrainExperiment').replace('guardedArrivalStop','quietStrainStop')
    if checkpoint==140:
        source=once(source,'candidate.reviewStepCorrections<=2','candidate.reviewStepCorrections<=1')
        source=source.replace('fixed <=2-QP ordinary-step work gate','fixed <=1-QP floor work gate')
        source=once(source,'guard median<=1.10','guard median<=0.80')
        source=source.replace('fixed median <=1.10 ordinary-step overhead gate','fixed median <=0.80 floor speed gate')
    return source

def trajectory_source(source):
    source=arrival_trajectory(source).replace('arrivalStopExperiment','quietStrainExperiment').replace('guardedArrivalStop','quietStrainStop')
    source=once(source,'    if !preflight {guard settledPhases.count==2', '    let totalQPs=records.reduce(0){$0+($1["candidateQPs"] as! Int)},controlQPs=records.reduce(0){$0+($1["controlQPs"] as! Int)}\n    result["candidateQPs"]=totalQPs;result["controlQPs"]=controlQPs;try persist()\n    guard totalQPs<controlQPs else {throw RopePhysicsError.invalid("early termination must reduce QP count")}\n    if !preflight {guard settledPhases.count==2')
    return source
