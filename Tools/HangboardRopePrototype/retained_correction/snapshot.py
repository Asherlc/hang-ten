from armijo.snapshot import once

def solver_source(source,diagnostic=False,physical_wood=False):
 source=once(source,'    var stationaryResidualExperiment=false','    var stationaryResidualExperiment=false\n    var retainedCorrectionExperiment=false\n    var retainedPhysicalWoodExperiment=false\n    private var retainedStepAccepted=false\n    private var retainedTrialInProgress=false\n    private var retainedTrial:RetainedTrial?')
 source=once(source,'        for _ in 0..<(stationaryAccepted ? 0:80) {',"""        retainedStepAccepted=false
        if !stationaryAccepted && retainedCorrectionExperiment && stationaryRetryDepth==0,
           dt==lastStepDuration,stationaryContextTime==time,residualContext != nil {
            let normalPath=self
            state=old;state.orientation=prediction.orientation
            for r in state.ropes.indices {for (i,local) in state.ropes[r].attachments {state.ropes[r].positions[i]=state.worldPoint(local)}}
            do {
                try RopePassageTopology.refresh(state:&state,input:input)
                RetainedCorrectionTrace.attempts += 1
                if try attemptRetainedCorrection(prediction:prediction,old:old) {
                    retainedStepAccepted=true;lastCorrectionFullStep=false
                    #if DEBUG
                    reviewConverged=true
                    #endif
                } else {self=normalPath;RetainedCorrectionTrace.rejections += 1}
            } catch {self=normalPath;RetainedCorrectionTrace.rejections += 1}
        }
        for _ in 0..<((stationaryAccepted || retainedStepAccepted) ? 0:80) {""")
 source=once(source,'stationaryContextEligible=residualContext != nil && (stationaryAccepted || lastCorrectionFullStep)',
                  'stationaryContextEligible=residualContext != nil && (stationaryAccepted || retainedStepAccepted || lastCorrectionFullStep)')
 source=once(source,'    private mutating func postStepResidual(prediction:RopeSimulationState)->Double? {',"""    private struct RetainedTrial {
        let particles:[[SIMD3<Double>]]
        let height:Double
        let context:ResidualContext
        let weights:[[Double]]
    }
    var reviewRetainedStepAccepted:Bool {retainedStepAccepted}
    private mutating func postStepResidual(prediction:RopeSimulationState)->Double? {
        retainedTrial=nil""")
 source=once(source,'        guard maximum.isFinite else{return nil}\n        if preconditionedResidualExperiment',"""        guard maximum.isFinite else{return nil}
        if retainedCorrectionExperiment {
            var raw=Array(repeating:0.0,count:rows.count)
            for k in 0..<eqCount {
                guard let v=context.rowVariables[k] else{return nil}
                raw[ids[k]]=context.multipliers[context.equalityIDs[k]]+estimated.base[v]
                guard raw[ids[k]].isFinite else{return nil}
            }
            for k in context.activeIDs.indices {raw[ids[eqCount+k]]=mapped[ids[eqCount+k]]!}
            let updated=ResidualContext(factor:context.factor,variables:context.variables,
                equalityIDs:Array(ids.prefix(eqCount)),rowVariables:context.rowVariables,
                activeIDs:Array(ids.suffix(context.activeIDs.count)),multipliers:raw,rows:rows)
            retainedTrial=RetainedTrial(particles:particles,height:estimated.border[0],context:updated,weights:weights)
        }
        if preconditionedResidualExperiment""")
 if physical_wood:
  source=once(source,'                } else if value < -1e-8 {return nil}', '''                } else if value < -1e-8 {
                    if retainedTrialInProgress && retainedPhysicalWoodExperiment && row.woodHit != nil {
                        RetainedCorrectionTrace.omittedWoodRows += 1
                        RetainedCorrectionTrace.omittedWoodDeficit=max(RetainedCorrectionTrace.omittedWoodDeficit,-value)
                    } else {return nil}
                }''')
 if diagnostic:
  source=once(source,'                } else if value < -1e-8 {return nil}', '                } else if value < -1e-8 {RetainedCorrectionTrace.stage="inactive source=\\(row.sourceID ?? \"nil\") wood=\\(row.woodHit != nil) value=\\(value)";return nil}')
  source=once(source,'        guard let context=residualContext else{return nil}', '        if retainedCorrectionExperiment {RetainedCorrectionTrace.stage="missing context"}\n        guard let context=residualContext else{return nil}')
  source=once(source,'        let rows=fresh.0,weights=fresh.1','        let rows=fresh.0,weights=fresh.1\n        if retainedCorrectionExperiment {RetainedCorrectionTrace.stage="canonical correspondence"}')
  source=once(source,'        guard Set(ids).count==ids.count else{return nil}', '        if retainedCorrectionExperiment {RetainedCorrectionTrace.stage="duplicate correspondence"}\n        guard Set(ids).count==ids.count else{return nil}')
  source=once(source,'        do {estimated=try context.factor.solve', '        if retainedCorrectionExperiment {RetainedCorrectionTrace.stage="retained solve"}\n        do {estimated=try context.factor.solve')
  source=once(source,'        var mapped:[Int:Double]=[:]', '        if retainedCorrectionExperiment {RetainedCorrectionTrace.stage="updated compression"}\n        var mapped:[Int:Double]=[:]')
  source=once(source,'        for id in rows.indices {\n            let row=rows[id]\n            var value=row.residual+row.boardGradient*estimated.border[0]', '        if retainedCorrectionExperiment {RetainedCorrectionTrace.stage="all fresh inactive separation"}\n        for id in rows.indices {\n            let row=rows[id]\n            var value=row.residual+row.boardGradient*estimated.border[0]')
  source=once(source,'        guard maximum.isFinite else{return nil}\n        if retainedCorrectionExperiment {', '        if retainedCorrectionExperiment {RetainedCorrectionTrace.stage="finite estimate"}\n        guard maximum.isFinite else{return nil}\n        if retainedCorrectionExperiment {')
 return source+"""
extension RopeDynamicsSolver {
    private mutating func attemptRetainedCorrection(prediction:RopeSimulationState,old:RopeSimulationState)throws->Bool {
        retainedTrialInProgress=true
        defer {retainedTrialInProgress=false}
        guard let _=postStepResidual(prediction:prediction),let trial=retainedTrial else {
            RetainedCorrectionTrace.reason="initial fresh correspondence/separation: "+RetainedCorrectionTrace.stage;return false
        }
        guard Self.correctionFraction(ropes:state.ropes,corrections:trial.particles,heightCorrection:trial.height)==1 else {
            RetainedCorrectionTrace.reason="original full-step trust";return false
        }
        let penalty=max(1,2*(trial.context.multipliers.map{abs($0)}.max() ?? 0))
        let score=try merit(state,prediction:prediction,weights:trial.weights,penalty:penalty)
        if retainedPhysicalWoodExperiment {RetainedCorrectionTrace.beforeParts=try retainedMeritDiagnostic(state,prediction:prediction,weights:trial.weights)}
        state.boardHeight += trial.height
        for r in state.ropes.indices {
            for i in state.ropes[r].positions.indices {state.ropes[r].positions[i] += trial.particles[r][i]}
            for (i,local) in state.ropes[r].attachments {state.ropes[r].positions[i]=state.worldPoint(local)}
        }
        try RopePassageTopology.refresh(state:&state,input:input)
        residualContext=trial.context // provisional FULL primal/dual update
        let proposedScore=try merit(state,prediction:prediction,weights:trial.weights,penalty:penalty)
        if retainedPhysicalWoodExperiment {RetainedCorrectionTrace.afterParts=try retainedMeritDiagnostic(state,prediction:prediction,weights:trial.weights)}
        RetainedCorrectionTrace.meritBefore=score;RetainedCorrectionTrace.meritAfter=proposedScore
        guard proposedScore<=score+1e-18 else {
            if retainedPhysicalWoodExperiment {
                // Diagnostic after rejection; never feeds the acceptance decision.
                let rejected=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1})
                RetainedCorrectionTrace.rejectedGeometryAccepted=rejected.geometryAccepted
                RetainedCorrectionTrace.rejectedClearanceMargin=rejected.minimumClearanceMargin
            }
            RetainedCorrectionTrace.reason="original merit";return false
        }
        let arrived=abs(simd_dot(state.orientation.vector,residualTarget.vector))>1-1e-12
        guard let remaining=postStepResidual(prediction:prediction),remaining<(arrived ? 0.001*residualDt:0.00005),physicalResidualFeasible() else {
            RetainedCorrectionTrace.reason="fresh endpoint residual/physical";return false
        }
        if retainedPhysicalWoodExperiment {
            let physical=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1})
            guard physical.geometryAccepted else{RetainedCorrectionTrace.reason="uncached original mesh physical";return false}
        }
        RetainedCorrectionTrace.remaining=remaining
        for id in trial.context.equalityIDs {
            let row=trial.context.rows[id]
            if let link=row.lengthSegment {distanceTension[row.rope][link]=max(0,trial.context.multipliers[id])}
        }
        // Old certified admission hints remain hints; the updated context is
        // tentative until ordinary final original-mesh/CCD acceptance commits.
        RetainedCorrectionTrace.reason="provisional pass"
        return true
    }
    private mutating func retainedMeritDiagnostic(_ candidate:RopeSimulationState,prediction:RopeSimulationState,weights:[[Double]])throws->[String:Double] {
        let evaluation=configurationEvaluation(candidate)
        var objective=0.5*state.boardMass*pow(candidate.boardHeight-prediction.boardHeight,2)
        var length=0.0,wood=0.0,portals=0.0,selfContacts=0.0,cordContacts=0.0
        for (r,rope) in candidate.ropes.enumerated() {
            for i in rope.positions.indices where weights[r][i]>0 {
                objective += 0.5*simd_length_squared(rope.positions[i]-prediction.ropes[r].positions[i])/weights[r][i]
            }
            for i in rope.restLengths.indices {
                length += abs(simd_distance(rope.positions[i],rope.positions[i+1])-rope.restLengths[i])
                wood += max(0,(evaluation.merits[r][i].map{$0.penetrationDepth}.max() ?? 0)-Self.contactLinearTolerance)
            }
            for pair in evaluation.selfPairs[r] {
                let points=RopeTriangleCollider.segmentPair(rope.positions[pair.x],rope.positions[pair.x+1],rope.positions[pair.y],rope.positions[pair.y+1])
                selfContacts += max(0,2*rope.radius+0.00005-simd_distance(points.0,points.1)-Self.contactLinearTolerance)
            }
            for (id,crossing) in rope.portalCrossings {
                guard let portal=portalMap[id] else{throw RopePhysicsError.invalid("Missing diagnostic portal")}
                let margin=RopePassageTopology.boundaryMargin(candidate.boardPoint(crossing.point(in:rope.positions)),portal:portal)
                portals += max(0,rope.radius+RopeRegionGeometry.clearance-margin-Self.contactLinearTolerance)
            }
        }
        for first in candidate.ropes.indices {for second in candidate.ropes.indices where second>first {
            for contact in evaluation.cordContacts[SIMD2(first,second)]! {cordContacts += max(0,contact.targetDistance-contact.distance-Self.contactLinearTolerance)}
        }}
        return ["objective":objective,"length":length,"wood":wood,"portals":portals,"self":selfContacts,"cord":cordContacts]
    }
}
enum RetainedCorrectionTrace {
    static var attempts=0,rejections=0
    static var reason="ineligible",stage="uninstrumented",remaining=Double.nan
    static var omittedWoodRows=0,omittedWoodDeficit=0.0,meritBefore=Double.nan,meritAfter=Double.nan
    static var rejectedGeometryAccepted=false,rejectedClearanceMargin=Double.nan
    static var beforeParts:[String:Double]=[:],afterParts:[String:Double]=[:]
}
"""
