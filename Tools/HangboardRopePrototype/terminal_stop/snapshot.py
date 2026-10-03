"""Isolated pre-update stationarity convergence; full fresh QP remains mandatory."""
from pathlib import Path


def solver_source(text):
    text=text.replace('    private var lastCorrectionFullStep=false', '''    private var lastCorrectionFullStep=false
    #if DEBUG
    private(set) var reviewTerminalStops=0
    #endif
    private struct CorrectionProgress {
        let movement:Double
        let stationary:Bool
    }''')
    text=text.replace('        candidate.reviewStepCorrections = 0', '        candidate.reviewStepCorrections = 0\n        candidate.reviewTerminalStops = 0')
    old='''            let movement=try correctConstraints(prediction:prediction)
            let arrivedNow=abs(simd_dot(state.orientation.vector,targetOrientation.vector))>1-1e-12
            let limit=convergenceExperiment ? (arrivedNow ? 0.001*dt:0.00005):1e-8'''
    new='''            let arrivedNow=abs(simd_dot(state.orientation.vector,targetOrientation.vector))>1-1e-12
            let limit=convergenceExperiment ? (arrivedNow ? 0.001*dt:0.00005):1e-8
            let progress=try correctConstraints(prediction:prediction,
                terminalLimit:convergenceExperiment && lastCorrectionFullStep ? limit:nil)
            if progress.stationary {
                #if DEBUG
                reviewConverged=true
                #endif
                break
            }
            let movement=progress.movement'''
    assert text.count(old)==1
    text=text.replace(old,new)
    needle='''        #if DEBUG
        var reviewConverged = false'''
    assert text.count(needle)==1
    text=text.replace(needle,'        lastCorrectionFullStep=false\n'+needle)
    old='    private mutating func correctConstraints(prediction:RopeSimulationState) throws -> Double {'
    assert text.count(old)==1
    text=text.replace(old,'    private mutating func correctConstraints(prediction:RopeSimulationState,terminalLimit:Double?=nil) throws -> CorrectionProgress {')
    needle='        let penalty=max(1,2*(lambda.map{abs($0)}.max() ?? 0))'
    assert text.count(needle)==1
    text=text.replace(needle,'''        if Self.terminalEligible(limit:terminalLimit,norm:max(maximum,abs(heightCorrection)),
            strain:maximumStrain(),trust:alpha,previousAcceptedFullStep:lastCorrectionFullStep) {
            #if DEBUG
            reviewTerminalStops += 1
            #endif
            return CorrectionProgress(movement:max(maximum,abs(heightCorrection)),stationary:true)
        }
'''+needle)
    old='                    return (convergenceExperiment ? 1:alpha)*max(maximum,abs(heightCorrection))'
    assert text.count(old)==1
    text=text.replace(old,'                    return CorrectionProgress(movement:(convergenceExperiment ? 1:alpha)*max(maximum,abs(heightCorrection)),stationary:false)')
    return text+'\n'+(Path(__file__).parent/'Eligibility.swift').read_text()
