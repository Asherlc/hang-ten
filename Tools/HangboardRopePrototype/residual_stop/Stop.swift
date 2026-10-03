// Snapshot-only estimate. No estimated position or multiplier is ever applied.
extension RopeDynamicsSolver {
    private struct ResidualContext {
        let factor:RopeContactSystem.ResidualOperator
        let variables:[[SIMD3<Int>]]
        let equalityIDs:[Int]
        let rowVariables:[Int:Int]
        let activeIDs:[Int]
        let multipliers:[Double]
        let rows:[ConstraintRow]
    }
    private mutating func postStepResidual(prediction:RopeSimulationState)->Double? {
        guard let context=residualContext else{return nil}
        let fresh:([ConstraintRow],[[Double]])
        do {fresh=try buildConstraintRows(prediction:prediction)} catch {return nil}
        let rows=fresh.0,weights=fresh.1
        var buckets:[String:[Int]]=[:]
        for id in rows.indices {if let source=rows[id].sourceID {buckets[source,default:[]].append(id)}}
        var ids:[Int]=[]
        for oldID in context.equalityIDs+context.activeIDs {
            let old=context.rows[oldID]
            guard let source=old.sourceID,let found=buckets[source],found.count==1 else{return nil}
            let id=found[0],row=rows[id]
            guard row.rope==old.rope,row.particles==old.particles,row.secondRope==old.secondRope,
                  row.contact==old.contact,row.lengthSegment==old.lengthSegment else{return nil}
            ids.append(id)
        }
        guard Set(ids).count==ids.count else{return nil}
        let eqCount=context.equalityIDs.count
        var rhs=Array(repeating:0.0,count:context.factor.factor.baseCount)
        var borderRHS=[-state.boardMass*(state.boardHeight-prediction.boardHeight)]
        for r in state.ropes.indices {for i in state.ropes[r].positions.indices where weights[r][i]>0 {
            let offset=state.ropes[r].positions[i]-prediction.ropes[r].positions[i]
            for a in 0..<3 {rhs[context.variables[r][i][a]] = -offset[a]/weights[r][i]}
        }}
        var contactResiduals:[Double]=[]
        for k in ids.indices {
            let row=rows[ids[k]],oldID=(context.equalityIDs+context.activeIDs)[k]
            let multiplier=context.multipliers[oldID]
            for j in row.particles.indices {for a in 0..<3 {
                let variable=context.variables[row.ropeIndex(j)][row.particles[j]][a]
                if variable>=0 {rhs[variable] -= row.gradients[j][a]*multiplier}
            }}
            borderRHS[0] -= row.boardGradient*multiplier
            let residual=row.residual-1e-8*multiplier
            if k<eqCount {
                guard let v=context.rowVariables[k] else{return nil}
                rhs[v] = -residual
            } else {contactResiduals.append(residual)}
        }
        let estimated:(base:[Double],border:[Double],contactDelta:[Double])
        do {estimated=try context.factor.solve(rhs:rhs,borderRHS:borderRHS,contactResiduals:contactResiduals)} catch{return nil}
        var particles=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
        var maximum=abs(estimated.border[0])
        for r in particles.indices {for i in particles[r].indices where weights[r][i]>0 {
            let v=context.variables[r][i]
            particles[r][i]=SIMD3(estimated.base[v.x],estimated.base[v.y],estimated.base[v.z])
            maximum=max(maximum,simd_length(particles[r][i]))
        }}
        var mapped:[Int:Double]=[:]
        for k in context.activeIDs.indices {
            let multiplier=context.multipliers[context.activeIDs[k]]+estimated.contactDelta[k]
            guard multiplier.isFinite,multiplier<=0 else{return nil}
            mapped[ids[eqCount+k]]=multiplier
        }
        // Apply the original affine inactive separation tolerance to every fresh row.
        for id in rows.indices {
            let row=rows[id]
            var value=row.residual+row.boardGradient*estimated.border[0]
            for j in row.particles.indices {value += simd_dot(row.gradients[j],particles[row.ropeIndex(j)][row.particles[j]])}
            guard value.isFinite else{return nil}
            if row.contact {
                if let multiplier=mapped[id] {
                    guard abs(value-1e-8*multiplier)<=1e-8 else{return nil}
                } else if value < -1e-8 {return nil}
            } else {
                guard let k=ids.prefix(eqCount).firstIndex(of:id),let v=context.rowVariables[k] else{return nil}
                let multiplier=context.multipliers[context.equalityIDs[k]]+estimated.base[v]
                guard abs(value-1e-8*multiplier)<=1e-8 else{return nil}
            }
        }
        ResidualStopTrace.eligible += 1
        return maximum
    }
}

enum ResidualStopTrace {
    static var enabled=ProcessInfo.processInfo.environment["HANGTEN_REVIEW_RESIDUAL_STOP"] == "1"
    static var eligible=0
    static var stops=0
}
