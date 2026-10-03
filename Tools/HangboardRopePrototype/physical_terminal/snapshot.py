"""User-authorized physical-feasibility stopping, with fresh original QP."""
from terminal_stop.snapshot import solver_source as terminal_source
from pathlib import Path


def solver_source(text):
    text=terminal_source(text)
    text=text.replace('        let stationary:Bool','        let stationary:Bool\n        var geometry:(RopeSimulationMetrics,[[Double]])?=nil')
    text=text.replace('        lastCorrectionFullStep=false\n        #if DEBUG\n        var reviewConverged',
                      '        var terminalGeometry:(RopeSimulationMetrics,[[Double]])?=nil\n        lastCorrectionFullStep=false\n        #if DEBUG\n        var reviewConverged')
    text=text.replace('            if progress.stationary {','            if progress.stationary {\n                terminalGeometry=progress.geometry')
    text=text.replace('        if Self.terminalEligible(limit:terminalLimit,norm:max(maximum,abs(heightCorrection)),\n            strain:maximumStrain(),trust:alpha,previousAcceptedFullStep:lastCorrectionFullStep) {',
'''        if Self.physicalTerminalEligible(limit:terminalLimit,norm:max(maximum,abs(heightCorrection)),
            trust:alpha,previousAcceptedFullStep:lastCorrectionFullStep) {
            var bounds=state.ropes.map{Array(repeating:Double.infinity,count:$0.restLengths.count)}
            let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,
                boardHistory:[state.boardHeight],channelCache:channelColliderCache,
                clearanceReceipts:evaluation.clearances,clearanceObserver:{r,i,value in bounds[r][i]=value})
            if metrics.geometryAccepted {''')
    old='            return CorrectionProgress(movement:max(maximum,abs(heightCorrection)),stationary:true)\n        }'
    assert text.count(old)==1
    text=text.replace(old,'            return CorrectionProgress(movement:max(maximum,abs(heightCorrection)),stationary:true,geometry:(metrics,bounds))\n            }\n        }')
    old='''        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceReceipts:receipts,clearanceObserver:{r,i,value in perSegment[r][i]=value})'''
    assert text.count(old)==1
    text=text.replace(old,'''        let metrics:RopeSimulationMetrics
        if let (geometry,bounds)=terminalGeometry {
            perSegment=bounds
            var speed=abs(state.boardVerticalVelocity)
            for rope in state.ropes {for velocity in rope.velocities {speed=max(speed,simd_length(velocity))}}
            let heights=history.map{$0.1}
            metrics=RopeSimulationMetrics(totalLengthError:geometry.totalLengthError,
                maximumLocalStrain:geometry.maximumLocalStrain,minimumSegmentClearance:geometry.minimumSegmentClearance,
                minimumClearanceMargin:geometry.minimumClearanceMargin,topologyValid:geometry.topologyValid,
                topologyFailure:geometry.topologyFailure,maximumSpeed:speed,
                boardDisplacement:(heights.max() ?? state.boardHeight)-(heights.min() ?? state.boardHeight))
        } else {
            metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceReceipts:receipts,clearanceObserver:{r,i,value in perSegment[r][i]=value})
        }''')
    return text+'\n'+(Path(__file__).parent/'Eligibility.swift').read_text()
