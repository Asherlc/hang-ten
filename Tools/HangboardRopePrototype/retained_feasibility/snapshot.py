from armijo.snapshot import once
from retained_correction.snapshot import solver_source as retained_source


def solver_source(source):
    source = retained_source(source, physical_wood=True)
    source = once(source, "let trial=retainedTrial else {", "var trial=retainedTrial else {")
    source = once(source, "        let score=try merit(state,prediction:prediction,weights:trial.weights,penalty:penalty)",
                  "        let trialStart=state\n        let score=try merit(state,prediction:prediction,weights:trial.weights,penalty:penalty)")
    source = once(source, "        residualContext=trial.context // provisional FULL primal/dual update", """        // One feasibility correction; zero objective and non-length forcing.
        var rhs=Array(repeating:0.0,count:trial.context.factor.factor.baseCount)
        for k in trial.context.equalityIDs.indices {
            let id=trial.context.equalityIDs[k],row=trial.context.rows[id]
            guard let link=row.lengthSegment,let v=trial.context.rowVariables[k] else {
                RetainedCorrectionTrace.reason="non-length equality in feasibility map";return false
            }
            let rope=state.ropes[row.rope]
            let residual=simd_distance(rope.positions[link],rope.positions[link+1])-rope.restLengths[link]
            rhs[v] = -(residual-1e-8*trial.context.multipliers[id])
        }
        let feasibility=try trial.context.factor.solve(rhs:rhs,borderRHS:[0],
            contactResiduals:Array(repeating:0,count:trial.context.activeIDs.count))
        RetainedCorrectionTrace.feasibilitySolves += 1
        var raw=trial.context.multipliers
        for k in trial.context.equalityIDs.indices {
            guard let v=trial.context.rowVariables[k] else{return false}
            raw[trial.context.equalityIDs[k]] += feasibility.base[v]
        }
        for k in trial.context.activeIDs.indices {
            let id=trial.context.activeIDs[k]
            raw[id] += feasibility.contactDelta[k]
            guard raw[id].isFinite,raw[id]<=0 else {
                RetainedCorrectionTrace.reason="feasibility updated compression";return false
            }
        }
        guard raw.allSatisfy({$0.isFinite}),feasibility.base.allSatisfy({$0.isFinite}),feasibility.border.allSatisfy({$0.isFinite}) else {
            RetainedCorrectionTrace.reason="feasibility finite";return false
        }
        var combined=trial.particles
        state.boardHeight += feasibility.border[0]
        for r in state.ropes.indices {
            for i in state.ropes[r].positions.indices where trial.weights[r][i]>0 {
                let v=trial.context.variables[r][i]
                let correction=SIMD3(feasibility.base[v.x],feasibility.base[v.y],feasibility.base[v.z])
                state.ropes[r].positions[i] += correction
                combined[r][i] += correction
            }
            for (i,local) in state.ropes[r].attachments {state.ropes[r].positions[i]=state.worldPoint(local)}
        }
        let combinedHeight=trial.height+feasibility.border[0]
        guard Self.correctionFraction(ropes:trialStart.ropes,corrections:combined,heightCorrection:combinedHeight)==1 else {
            RetainedCorrectionTrace.reason="combined original trust";return false
        }
        try RopePassageTopology.refresh(state:&state,input:input)
        let updated=ResidualContext(factor:trial.context.factor,variables:trial.context.variables,
            equalityIDs:trial.context.equalityIDs,rowVariables:trial.context.rowVariables,
            activeIDs:trial.context.activeIDs,multipliers:raw,rows:trial.context.rows)
        trial=RetainedTrial(particles:combined,height:combinedHeight,context:updated,weights:trial.weights)
        residualContext=trial.context // provisional full primal/dual feasibility update
        retainedTrialInProgress=false // ALL inactive wood guards required at combined endpoint""")
    source = once(source, '    static var attempts=0,rejections=0', '    static var feasibilitySolves=0\n    static var attempts=0,rejections=0')
    return source
