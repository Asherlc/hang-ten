import Foundation

/// Experimental nonlinear primal-dual primitives; not linked into the app.
enum NonlinearPrimalDual {
    static let epsilon=1e-8
    static func eliminate(s:Double,v:Double,h:Double,rc:Double) throws -> (diagonal:Double,load:Double) {
        guard s.isFinite,s>0,v.isFinite,v>0,h.isFinite,rc.isFinite else {throw RopePhysicsError.invalid("Invalid positive primal-dual contact")}
        let denominator=v+epsilon*s
        let diagonal=s/denominator,load=(rc-s*h)/denominator
        guard diagonal.isFinite,load.isFinite,diagonal>0 else {throw RopePhysicsError.invalid("Nonfinite eliminated contact")}
        return (diagonal,load)
    }
    static func recover(s:Double,v:Double,h:Double,rc:Double,jdx:Double) throws -> (s:Double,v:Double) {
        guard jdx.isFinite else {throw RopePhysicsError.invalid("Nonfinite contact Jacobian product")}
        let e=try eliminate(s:s,v:v,h:h,rc:rc)
        let ds=e.load-e.diagonal*jdx,dv=jdx+epsilon*ds+h
        guard ds.isFinite,dv.isFinite else {throw RopePhysicsError.invalid("Nonfinite recovered contact direction")}
        return (ds,dv)
    }
    static func fraction(values:[Double],change:[Double],safety:Double) throws -> Double {
        guard values.count==change.count,values.allSatisfy({$0.isFinite && $0>0}),change.allSatisfy({$0.isFinite}),
              safety.isFinite,safety>0,safety<=1 else {throw RopePhysicsError.invalid("Invalid fraction-to-boundary input")}
        var result=1.0
        for i in values.indices where change[i]<0 {result=min(result,-safety*values[i]/change[i])}
        return result
    }
}

/// Original-matrix certified mixed saddle solve, with a shared last height DOF.
final class NonlinearPrimalDualFactor {
    let size:Int
    let backend:String
    private let entries:[(Int,Int,Double)]
    private let band:RopeBandedFactorization?
    private let sparse:SparseLDL?
    private(set) var solveCalls=0
    private(set) var refinementSolves=0
    private(set) var maximumResidual=0.0
    init(size:Int,equalities:Set<Int>,entries:[(Int,Int,Double)]) throws {
        guard size>=2,size<=50_256,equalities.allSatisfy({(0..<size-1).contains($0)}),entries.count<=8_000_000,
              entries.allSatisfy({(0..<size).contains($0.0) && (0..<size).contains($0.1) && $0.2.isFinite}) else {
            throw RopePhysicsError.invalid("Invalid coupled nonlinear matrix")
        }
        self.size=size
        var combined:[Int:Double]=[:]
        for (i,j,value) in entries {combined[min(i,j)*size+max(i,j),default:0] += value}
        let keys=combined.keys.sorted()
        let values=keys.map{combined[$0]!}
        let ordered=keys.map{($0%size,$0/size,combined[$0]!)}
        self.entries=ordered
        let width=min(6,size-2)
        if ordered.allSatisfy({$0.0==size-1 || abs($0.0-$0.1)<=width}) {
            var system=try RopeBandedSystem(size:size-1,bandwidth:width)
            var column=Array(repeating:0.0,count:size-1),height=0.0
            for (r,c,v) in ordered {
                if r==size-1 {if c==size-1 {height += v}else {column[c] += v}}
                else {try system.addSymmetric(row:r,column:c,value:v)}
            }
            band=try system.factorized(borderColumns:[column],borderMatrix:[[height]])
            sparse=nil;backend="band-plus-shared-height"
        } else {
            var starts=[0],indices:[Int32]=[],column=0
            for key in keys {
                while column<key/size {starts.append(indices.count);column += 1}
                indices.append(Int32(key%size))
            }
            while starts.count<size+1 {starts.append(indices.count)}
            let factor=try SparseLDL(size:size,starts:starts,indices:indices,permutation:(0..<size).map{Int32($0)},equalities:equalities)
            try factor.refactor(values)
            sparse=factor;band=nil;backend="sparse-with-all-nonlocal-coupling"
        }
    }
    private func raw(_ rhs:[Double]) throws -> [Double] {
        solveCalls += 1
        if let band {
            let solved=try band.solve(rhs:Array(rhs.dropLast()),borderRHS:[rhs.last!])
            return solved.base+solved.border
        }
        return try sparse!.solve(rhs)
    }
    private func product(_ x:[Double])->[Double] {
        var result=Array(repeating:0.0,count:size)
        for (r,c,v) in entries {
            result[r] += v*x[c]
            if r != c {result[c] += v*x[r]}
        }
        return result
    }
    func solve(_ rhs:[Double]) throws -> [Double] {
        guard rhs.count==size,rhs.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Invalid nonlinear Newton load")}
        var x=try raw(rhs)
        for _ in 0..<3 {
            let error=zip(rhs,product(x)).map(-)
            if (error.map{abs($0)}.max() ?? 0)<=1e-12*max(1,rhs.map{abs($0)}.max() ?? 0) {break}
            refinementSolves += 1
            x=zip(x,try raw(error)).map(+)
        }
        let error=zip(rhs,product(x)).map{abs($0-$1)}.max() ?? 0
        maximumResidual=max(maximumResidual,error)
        guard error<=1e-10,x.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Original coupled Newton matrix certificate failed")}
        return x
    }
}
