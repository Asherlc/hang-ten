"""Explicit pre-QP stationary-pose residual experiment, never product adoption."""
from diagnostic_collection.snapshot import once
def solver_source(s):
 s=once(s,'    var preconditionedResidualExperiment=false',
 """    var preconditionedResidualExperiment=false
    var stationaryResidualExperiment=false
    private var stationaryResidualAccepted=false
    private var stationaryContextTime:Double?
    private var stationaryContextEligible=false""")
 s=once(s,'        let old=state',
 """        let old=state
        let oldEvaluation=cachedEvaluation
        let previousStationary=stationaryResidualAccepted
        stationaryResidualAccepted=false
        var stationaryAccepted=false""")
 s=once(s,'        for _ in 0..<80 {',
 """        // The objective still uses the original prediction. This is only an
        // experimental initial stopping check at the prior accepted pose.
        let oldSpeed=max(abs(old.boardVerticalVelocity),old.ropes.flatMap{$0.velocities}.map{simd_length($0)}.max() ?? 0)
        if stationaryResidualExperiment && convergenceExperiment && preconditionedResidualExperiment,
           dt==lastStepDuration,stationaryContextTime==time,stationaryContextEligible,
           (lastCorrectionFullStep || previousStationary),oldSpeed<0.001,
           state.orientation.vector==old.orientation.vector,
           abs(simd_dot(old.orientation.vector,targetOrientation.vector))>1-1e-12 {
            let normalPath=self
            state=old;cachedEvaluation=oldEvaluation
            if let estimate=postStepResidual(prediction:prediction),estimate<0.001*dt,physicalResidualFeasible() {
                stationaryAccepted=true;stationaryResidualAccepted=true
                lastCorrectionFullStep=false // no applied step; do not fabricate alpha=1
                #if DEBUG
                reviewConverged=true
                #endif
                StationaryResidualTrace.accepted += 1
                StationaryResidualTrace.estimates.append(estimate)
            } else {self=normalPath;StationaryResidualTrace.rejected += 1}
        }
        for _ in 0..<(stationaryAccepted ? 0:80) {""")
 s=once(s,'        lastStepDuration=dt',
 """        lastStepDuration=dt
        stationaryContextTime=time
        stationaryContextEligible=residualContext != nil && (stationaryAccepted || lastCorrectionFullStep)""")
 return s+'\nextension RopeDynamicsSolver {var reviewStationaryStepAccepted:Bool {stationaryResidualAccepted}}\n'
