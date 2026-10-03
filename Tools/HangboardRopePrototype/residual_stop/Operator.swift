extension RopeContactSystem {
    struct ResidualOperator:Sendable {
        let factor:RopeBandedFactorization
        let rows:[RopeLinearContact]
        let responses:[[Double]]
        let lower:[Double]
        func solve(rhs:[Double],borderRHS:[Double],contactResiduals:[Double]) throws
            -> (base:[Double],border:[Double],contactDelta:[Double]) {
            guard contactResiduals.count==rows.count else {throw Failure.infeasible}
            let value=try factor.solve(rhs:rhs,borderRHS:borderRHS)
            let size=value.base.count,n=rows.count
            var primal=value.base+value.border
            var delta=rows.indices.map{contactResiduals[$0]+rows[$0].dot(primal,size:size)}
            for i in 0..<n {
                for j in 0..<i {delta[i] -= lower[i*n+j]*delta[j]}
                delta[i] /= lower[i*n+i]
            }
            for i in (0..<n).reversed() {
                for j in (i+1)..<n {delta[i] -= lower[j*n+i]*delta[j]}
                delta[i] /= lower[i*n+i]
            }
            for k in 0..<n {for i in primal.indices {primal[i] -= responses[k][i]*delta[k]}}
            guard (primal+delta).allSatisfy({$0.isFinite}) else {throw Failure.illConditioned}
            return (Array(primal.prefix(size)),Array(primal.dropFirst(size)),delta)
        }
    }
}
