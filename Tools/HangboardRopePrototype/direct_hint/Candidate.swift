// Native-only proposal; every unsuccessful fresh KKT trial uses the original solver.
extension RopeDynamicsSolver {
    private func equalityHintVariables(rows:[ConstraintRow],weights:[[Double]]) -> [[SIMD3<Int>]]? {
        let equality=rows.filter{!$0.contact}
        guard equality.count==state.ropes.reduce(0,{$0+$1.restLengths.count}) else{return nil}
        var expected=0
        for r in state.ropes.indices {for i in state.ropes[r].restLengths.indices {
            let row=equality[expected]
            guard row.rope==r,row.particles==[i,i+1],row.lengthSegment==i,row.secondRope==nil else{return nil}
            expected+=1
        }}
        var variables=state.ropes.map{Array(repeating:SIMD3<Int>(repeating:-1),count:$0.positions.count)}
        var size=0
        for r in state.ropes.indices {for i in state.ropes[r].positions.indices {
            if weights[r][i]>0 {variables[r][i]=SIMD3(size,size+1,size+2);size+=3}
            if i<state.ropes[r].restLengths.count {size+=1}
        }}
        return variables
    }
    private mutating func oneShotHintCorrection(rows:[ConstraintRow],weights:[[Double]],prediction:RopeSimulationState) throws
        -> (particles:[[SIMD3<Double>]],height:Double,multipliers:[Double],ids:[Int])? {
        guard !contactHints.isEmpty,let equalityVariables=equalityHintVariables(rows:rows,weights:weights) else{return nil}
        HintCandidateTrace.attempts+=1
        let equalityIDs=rows.indices.filter{!rows[$0].contact},contactIDs=rows.indices.filter{rows[$0].contact}
        let contacts=contactIDs.map{id -> RopeLinearContact in
            let row=rows[id]
            var indices:[Int]=[],coefficients:[Double]=[]
            for k in row.particles.indices {for axis in 0..<3 {
                let variable=equalityVariables[row.ropeIndex(k)][row.particles[k]][axis]
                if variable>=0 {indices.append(variable);coefficients.append(row.gradients[k][axis])}
            }}
            return RopeLinearContact(indices:indices,coefficients:coefficients,border:[row.boardGradient],residual:row.residual)
        }
        var buckets:[[Int]:[Int]]=[:]
        for id in contacts.indices {buckets[contacts[id].indices,default:[]].append(id)}
        var initial:[Int:Double]=[:]
        // Identical hint mapping to the unchanged Schur path; values select only.
        for (old,multiplier) in contactHints where multiplier<0 {
            var chosen:Int?,best=Double.infinity
            for id in buckets[old.indices] ?? [] {
                let row=contacts[id]
                guard row.coefficients.count==old.coefficients.count,row.border.count==old.border.count else{continue}
                var error=0.0
                for k in row.coefficients.indices {let d=row.coefficients[k]-old.coefficients[k];error+=d*d}
                for k in row.border.indices {let d=row.border[k]-old.border[k];error+=d*d}
                if error<best {best=error;chosen=id}
            }
            if let chosen {initial[chosen,default:0]+=multiplier}
        }
        let selectedContacts=initial.keys.sorted()
        let ids=(equalityIDs+selectedContacts.map{contactIDs[$0]}).sorted()
        let prepared=try preparedHintBackbone(rows:ids.map{rows[$0]},weights:weights,prediction:prediction)
        let factor=try prepared.system.factorized(borderColumns:prepared.columns,borderMatrix:prepared.border)
        let solved=try factor.solve(rhs:prepared.rhs,borderRHS:prepared.borderRHS)
        var multipliers=Array(repeating:0.0,count:ids.count)
        for id in prepared.local {multipliers[id]=solved.base[prepared.rowVariables[id]!]}
        for (offset,id) in prepared.borderRows.enumerated() {multipliers[id]=solved.border[offset+1]}
        var particles=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
        for r in particles.indices {for i in particles[r].indices where weights[r][i]>0 {
            let v=prepared.variables[r][i]
            particles[r][i]=SIMD3(solved.base[v.x],solved.base[v.y],solved.base[v.z])
        }}
        let originalResidual=prepared.system.hintResidual(base:solved.base,border:solved.border,rhs:prepared.rhs,
            columns:prepared.columns,borderMatrix:prepared.border,borderRHS:prepared.borderRHS)
        guard originalResidual.isFinite,originalResidual<=1e-10 else{return nil}
        let selected=Dictionary(uniqueKeysWithValues:zip(ids,multipliers))
        for id in rows.indices {
            let row=rows[id]
            var value=row.residual+row.boardGradient*solved.border[0]
            for k in row.particles.indices {value+=simd_dot(row.gradients[k],particles[row.ropeIndex(k)][row.particles[k]])}
            guard value.isFinite else{return nil}
            if let lambda=selected[id] {
                guard abs(value-1e-8*lambda)<=1e-8 else{return nil}
                if row.contact && (lambda>0 || value < -1e-8) {return nil}
            } else {
                guard row.contact,value >= -1e-8 else{return nil}
            }
        }
        contactHints=selectedContacts.map{(contacts[$0],selected[contactIDs[$0]]!)}
        HintCandidateTrace.accepted+=1
        return (particles,solved.border[0],multipliers,ids)
    }
}
enum HintCandidateTrace {
    static var attempts=0,accepted=0,exceptions=0
    static func reset(){attempts=0;accepted=0;exceptions=0}
}
