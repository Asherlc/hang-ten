import Foundation

/// An inequality J dq + C >= 0 in one frozen chain linearization.
struct RopeLinearContact: Sendable {
    let indices: [Int]
    let coefficients: [Double]
    let border: [Double]
    let residual: Double

    fileprivate func dot(_ vector: [Double], size: Int) -> Double {
        var value=0.0
        for k in indices.indices {value += coefficients[k]*vector[indices[k]]}
        for k in border.indices {value += border[k]*vector[size+k]}
        return value
    }
}

/// Factor the equality backbone once, then update its contact-space Cholesky
/// factor as inequalities enter and leave. All inactive inequalities are
/// separated before returning; none are discarded on grounds of dependence.
enum RopeContactSystem {
    enum Failure: Error {case iterationLimit, illConditioned, infeasible}
    struct Solution: Sendable {
        let base: [Double]
        let border: [Double]
        let multipliers: [Double]
        let activeIDs: [Int]
    }

    static func solve(factor: RopeBandedFactorization, base: [Double], border: [Double],
                      contacts: [RopeLinearContact], initialMultipliers: [Int: Double]=[:],
                      maxIterations: Int=2048, fallback: (() throws -> Solution)?=nil) throws -> Solution {
        do {
            return try solveFactored(factor:factor,base:base,border:border,contacts:contacts,
                                     initialMultipliers:initialMultipliers,maxIterations:maxIterations)
        } catch Failure.illConditioned {
            // Forming J K^-1 J^T can lose the small regularizer for scaled,
            // dependent rows. Retry the original explicitly regularized KKT;
            // this is not permission to discard an inequality.
            guard let fallback else {throw Failure.illConditioned}
            return try fallback()
        }
    }

    private static func solveFactored(factor: RopeBandedFactorization, base: [Double], border: [Double],
                                     contacts: [RopeLinearContact], initialMultipliers: [Int: Double],
                                     maxIterations: Int) throws -> Solution {
        let size=base.count,dimension=size+border.count
        guard size==factor.baseCount,border.count==factor.borderCount,
              size>0,dimension<=50_256,maxIterations>0,maxIterations<=2048,
              contacts.count<=100_000,(base+border).allSatisfy({$0.isFinite}),
              contacts.allSatisfy({row in
                  row.indices.count==row.coefficients.count && row.border.count==border.count &&
                  row.indices.allSatisfy({(0..<size).contains($0)}) && row.residual.isFinite &&
                  (row.coefficients+row.border).allSatisfy({$0.isFinite})
              }),initialMultipliers.allSatisfy({contacts.indices.contains($0.key) && $0.value.isFinite && $0.value<=0}) else {
            throw RopePhysicsError.invalid("Invalid rope contact system")
        }
        let unconstrained=base+border
        let residuals=contacts.map{$0.residual+$0.dot(unconstrained,size:size)}
        guard residuals.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite contact residual")}
        // Responses belong to this linearization only. Reusing one after a
        // Jacobian or Hessian change would solve a different physical problem.
        var responses: [Int: [Double]]=[:]
        let initialIDs=initialMultipliers.keys.sorted()
        guard initialIDs.count*dimension<=8_000_000 else {throw RopePhysicsError.invalid("Excessive rope contact response storage")}
        let batchCount=min(64,max(1,500_000/dimension))
        for start in stride(from:0,to:initialIDs.count,by:batchCount) {
            let ids=Array(initialIDs[start..<min(initialIDs.count,start+batchCount)])
            var rhs=Array(repeating:0.0,count:size*ids.count),borderRHS:[Double]=[]
            for (j,id) in ids.enumerated() {
                let row=contacts[id]
                for k in row.indices.indices {rhs[j*size+row.indices[k]] += row.coefficients[k]}
                borderRHS += row.border
            }
            let result=try factor.solveBatch(rhs:rhs,borderRHS:borderRHS,count:ids.count)
            let nb=border.count
            for (j,id) in ids.enumerated() {
                responses[id]=Array(result.base[j*size..<(j+1)*size])+Array(result.border[j*nb..<(j+1)*nb])
            }
        }
        func response(_ id: Int) throws -> [Double] {
            if let cached=responses[id] {return cached}
            guard (responses.count+1)*dimension<=8_000_000 else {
                throw RopePhysicsError.invalid("Excessive rope contact response storage")
            }
            let row=contacts[id]
            var rhs=Array(repeating:0.0,count:size)
            for k in row.indices.indices {rhs[row.indices[k]] += row.coefficients[k]}
            let solved=try factor.solve(rhs:rhs,borderRHS:row.border)
            let vector=solved.base+solved.border
            responses[id]=vector
            return vector
        }
        var active=initialMultipliers.keys.sorted(),dual=initialMultipliers
        var cholesky=ContactCholesky()
        for k in active.indices {
            let id=active[k],column=try response(id)
            try cholesky.append(cross:(0..<k).map{contacts[active[$0]].dot(column,size:size)},
                                diagonal:contacts[id].dot(column,size:size)+1e-8)
        }
        for _ in 0..<maxIterations {
            let lambda=try cholesky.solve(active.map{residuals[$0]})
            let blocking=RopeContactWorkingSet.blockingMultiplier(activeIDs:active,multipliers:lambda,
                contacts:Array(repeating:true,count:active.count),feasibleMultipliers:dual)
            if let blocking {
                for k in active.indices {
                    let previous=dual[active[k]] ?? 0
                    dual[active[k]]=previous+blocking.fraction*(lambda[k]-previous)
                }
                dual.removeValue(forKey:active[blocking.index])
                active.remove(at:blocking.index)
                try cholesky.remove(blocking.index)
                continue
            }
            dual=Dictionary(uniqueKeysWithValues:zip(active,lambda))
            var correction=unconstrained
            for k in active.indices {
                let column=try response(active[k])
                for i in correction.indices {correction[i] -= column[i]*lambda[k]}
            }
            guard correction.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite contact correction")}
            var selected=Array(repeating:false,count:contacts.count)
            for id in active {selected[id]=true}
            var worst: (id: Int, residual: Double)?
            for id in contacts.indices {
                let residual=contacts[id].residual+contacts[id].dot(correction,size:size)
                guard residual.isFinite else {throw RopePhysicsError.invalid("Nonfinite contact feasibility")}
                if selected[id] {
                    // The explicitly regularized KKT solves C + J dq =
                    // epsilon * lambda, not zero. Validate that equation and
                    // require an actual physical response for violated rows.
                    // A zero-gradient row must never be "solved" solely by
                    // its multiplier regularizer. Outer nonlinear acceptance
                    // still applies the unchanged physical clearance gate.
                    let multiplier=dual[id] ?? 0
                    guard abs(residual-1e-8*multiplier)<=1e-8 else {throw Failure.illConditioned}
                    if residual < -1e-8 {
                        let column=try response(id)
                        guard contacts[id].dot(column,size:size)>1e-8 else {throw Failure.infeasible}
                    }
                } else if residual < -1e-8 && residual<(worst?.residual ?? 0) {worst=(id,residual)}
            }
            if let worst {
                let column=try response(worst.id)
                try cholesky.append(cross:active.map{contacts[$0].dot(column,size:size)},
                                    diagonal:contacts[worst.id].dot(column,size:size)+1e-8)
                active.append(worst.id)
                continue
            }
            var multipliers=Array(repeating:0.0,count:contacts.count)
            for k in active.indices {multipliers[active[k]]=lambda[k]}
            return Solution(base:Array(correction.prefix(size)),border:Array(correction.dropFirst(size)),
                            multipliers:multipliers,activeIDs:active)
        }
        throw Failure.iterationLimit
    }

    private struct ContactCholesky {
        var count=0
        var lower: [Double]=[]

        mutating func append(cross: [Double], diagonal: Double) throws {
            let n=count
            guard cross.count==n,(n+1)*(n+1)<=8_000_000 else {
                throw RopePhysicsError.invalid("Invalid or excessive contact factor")
            }
            var vector=cross
            for i in 0..<n {
                for j in 0..<i {vector[i] -= lower[i*n+j]*vector[j]}
                vector[i] /= lower[i*n+i]
            }
            let pivot=diagonal-vector.reduce(0){$0+$1*$1}
            guard pivot>0,pivot.isFinite,vector.allSatisfy({$0.isFinite}) else {
                throw Failure.illConditioned
            }
            var next=Array(repeating:0.0,count:(n+1)*(n+1))
            for i in 0..<n {for j in 0...i {next[i*(n+1)+j]=lower[i*n+j]}}
            for j in 0..<n {next[n*(n+1)+j]=vector[j]}
            next[n*(n+1)+n]=sqrt(pivot)
            count += 1;lower=next
        }

        mutating func remove(_ index: Int) throws {
            let n=count
            guard (0..<n).contains(index) else {throw RopePhysicsError.invalid("Invalid contact release")}
            if n==1 {count=0;lower=[];return}
            let columns=n-1
            var upper=Array(repeating:0.0,count:n*columns)
            for r in 0..<n {for c in 0..<columns {
                let old=c<index ? c:c+1
                upper[r*columns+c]=lower[old*n+r]
            }}
            for k in index..<columns {
                let x=upper[k*columns+k],y=upper[(k+1)*columns+k],norm=hypot(x,y)
                guard norm>0,norm.isFinite else {throw Failure.illConditioned}
                let cosine=x/norm,sine=y/norm
                for j in k..<columns {
                    let a=upper[k*columns+j],b=upper[(k+1)*columns+j]
                    upper[k*columns+j]=cosine*a+sine*b
                    upper[(k+1)*columns+j] = -sine*a+cosine*b
                }
            }
            var next=Array(repeating:0.0,count:columns*columns)
            for i in 0..<columns {for j in 0...i {next[i*columns+j]=upper[j*columns+i]}}
            guard next.allSatisfy({$0.isFinite}),(0..<columns).allSatisfy({next[$0*columns+$0]>0}) else {
                throw Failure.illConditioned
            }
            count=columns;lower=next
        }

        func solve(_ rhs: [Double]) throws -> [Double] {
            var result=rhs
            for i in 0..<count {
                for j in 0..<i {result[i] -= lower[i*count+j]*result[j]}
                result[i] /= lower[i*count+i]
            }
            for i in (0..<count).reversed() {
                for j in (i+1)..<count {result[i] -= lower[j*count+i]*result[j]}
                result[i] /= lower[i*count+i]
            }
            guard result.allSatisfy({$0.isFinite}) else {throw Failure.illConditioned}
            return result
        }
    }
}
