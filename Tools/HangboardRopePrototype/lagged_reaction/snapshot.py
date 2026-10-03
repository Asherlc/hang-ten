"""Necessary lagged-reaction screen. No integration/product adoption."""
from pathlib import Path
from armijo.snapshot import once


def solver_source(source):
    start=source.index('        let old=state\n        let tensionScale=')
    end=source.index('        let prediction=state\n        cachedEvaluation=nil',start)
    # Exact copied original free predictor; no invented gravity or velocity update.
    predictor=source[start:end]
    extra='''
extension RopeDynamicsSolver {
    private mutating func laggedPredictorInPlace(dt:Double,targetOrientation:simd_quatd) {
'''+predictor+'''
    }
    func laggedFreePrediction(dt:Double,targetOrientation:simd_quatd)->RopeSimulationState {
        var scratch=self
        scratch.laggedPredictorInPlace(dt:dt,targetOrientation:targetOrientation)
        return scratch.state
    }
    func laggedProposal(previousPrediction:RopeSimulationState,previousSolved:RopeSimulationState,
        targetOrientation:simd_quatd)throws->RopeSimulationState {
        let dt=RopeLaggedReaction.h
        var proposed=laggedFreePrediction(dt:dt,targetOrientation:targetOrientation)
        // Retain original free-prediction topology guard before applying the reaction.
        try RopePassageTopology.refresh(state:&proposed,input:input)
        proposed.boardHeight=RopeLaggedReaction.position(proposed.boardHeight,previousSolved.boardHeight-previousPrediction.boardHeight)
        for r in proposed.ropes.indices {for i in proposed.ropes[r].positions.indices {
            if let support=proposed.ropes[r].supports[i] {proposed.ropes[r].positions[i]=support}
            else if let attachment=proposed.ropes[r].attachments[i] {proposed.ropes[r].positions[i]=proposed.worldPoint(attachment)}
            else {
                let reaction=previousSolved.ropes[r].positions[i]-previousPrediction.ropes[r].positions[i]
                for axis in 0..<3 {proposed.ropes[r].positions[i][axis]=RopeLaggedReaction.position(proposed.ropes[r].positions[i][axis],reaction[axis])}
            }
            proposed.ropes[r].velocities[i]=(proposed.ropes[r].positions[i]-state.ropes[r].positions[i])/dt
        }
        proposed.ropes[r].previousPositions=state.ropes[r].positions}
        proposed.boardVerticalVelocity=(proposed.boardHeight-state.boardHeight)/dt
        try RopePassageTopology.refresh(state:&proposed,input:input)
        return proposed
    }
}
'''
    return source+extra


def driver_source(source):
    return source[:source.index('func fixtures()throws {')]+Path(__file__).with_name('Main.swift').read_text()
