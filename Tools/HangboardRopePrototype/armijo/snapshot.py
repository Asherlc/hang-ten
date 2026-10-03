"""Original solver plus a stricter, guarded, native-only line search."""
def once(source,old,new):
    assert source.count(old)==1,old
    return source.replace(old,new)

def solver_source(source):
    source=once(source,'    private var lastStepDuration=1.0/240',
                '    private var lastStepDuration=1.0/240\n    var armijoExperiment=false')
    source=once(source,'        let score=try merit(state,prediction:prediction,weights:weights,penalty:penalty)',
                '''        let score=try merit(state,prediction:prediction,weights:weights,penalty:penalty)
        let armijoSlope=armijoExperiment ? armijoDirectionalDerivative(evaluation:evaluation,prediction:prediction,
            weights:weights,corrections:corrections,height:heightCorrection,penalty:penalty):nil
        var armijoRejected=0,originalRejected=0''')
    source=once(source,'if try merit(state,prediction:prediction,weights:weights,penalty:penalty)<=score+1e-18 {',
                '''let trialScore=try merit(state,prediction:prediction,weights:weights,penalty:penalty)
                let originalAccepted=trialScore<=score+1e-18
                let sufficient=armijoSlope.map{trialScore<=score+RopeArmijo.sigma*alpha*$0} ?? true
                if originalAccepted && sufficient {''')
    source=once(source,'                    lastCorrectionFullStep=alpha==1',
                '''                    ArmijoTrace.corrections.append(["movement":max(maximum,abs(heightCorrection)),"alpha":alpha,
                        "strain":maximumStrain(),"rows":rows.count,"slope":armijoSlope as Any? ?? NSNull(),
                        "armijoRejected":armijoRejected,"originalRejected":originalRejected])
                    lastCorrectionFullStep=alpha==1''')
    source=once(source,'            } catch RopePhysicsError.invalid { }\n            alpha *= 0.5',
                '''                if !originalAccepted {originalRejected += 1}
                else if !sufficient {armijoRejected += 1}
            } catch RopePhysicsError.invalid { }
            alpha *= 0.5''')
    # Append inside the solver's own file to access private cache/portal types.
    source+='''
extension RopeDynamicsSolver {
    private func armijoDirectionalDerivative(evaluation:RopeConfigurationEvaluation,prediction:RopeSimulationState,
        weights:[[Double]],corrections:[[SIMD3<Double>]],height:Double,penalty:Double)->Double? {
        guard state.ropes.count==1,evaluation.selfPairs.allSatisfy({$0.isEmpty}) else {return nil}
        for (r,rope) in state.ropes.enumerated() {
            for hits in evaluation.merits[r] {
                let argument=(hits.map{$0.penetrationDepth}.max() ?? 0)-Self.contactLinearTolerance
                guard RopeArmijo.inactiveHinge(argument) else {return nil}
            }
            for (id,crossing) in rope.portalCrossings {
                guard let portal=portalMap[id] else {return nil}
                let margin=RopePassageTopology.boundaryMargin(state.boardPoint(crossing.point(in:rope.positions)),portal:portal)
                let argument=rope.radius+RopeRegionGeometry.clearance-margin-Self.contactLinearTolerance
                guard RopeArmijo.inactiveHinge(argument) else {return nil}
            }
        }
        var objective=state.boardMass*(state.boardHeight-prediction.boardHeight)*height,violation=0.0
        for (r,rope) in state.ropes.enumerated() {
            for i in rope.positions.indices where weights[r][i]>0 {
                objective += simd_dot(rope.positions[i]-prediction.ropes[r].positions[i],corrections[r][i])/weights[r][i]
            }
            for i in rope.restLengths.indices {
                let edge=rope.positions[i+1]-rope.positions[i],length=simd_length(edge)
                guard length>1e-12 else {return nil}
                let a=RopeArmijo.displacement(rope,i,corrections[r][i],height)
                let b=RopeArmijo.displacement(rope,i+1,corrections[r][i+1],height)
                let rate=simd_dot(edge/length,b-a)
                violation += RopeArmijo.lengthSlope(residual:length-rope.restLengths[i],rate:rate)
            }
        }
        let slope=objective+penalty*violation
        return slope.isFinite && slope<0 ? slope:nil
    }
}
'''
    return source
