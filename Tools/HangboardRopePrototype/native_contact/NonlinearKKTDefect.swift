import Foundation

/// Experimental full residual correction, using an existing iteration factor.
enum NonlinearKKTDefect {
    struct Row {
        let jacobian:[(Int,Double)]
        let equalityVariable:Int?
        let s:Double,v:Double,ps:Double,pv:Double
        let originB:Double,trialB:Double,originH:Double,trialH:Double
    }
    struct Correction {
        let x:[Double],s:[Double],v:[Double],lambda:[Double]
        let remainderA:[Double],remainderB:[Double],remainderH:[Double],remainderSV:[Double]
        let stationarity:Double,equality:Double,contact:Double,complementarity:Double
    }
    static func solve(factor:NonlinearPrimalDualFactor,entries:[(Int,Int,Double)],masses:[Double],
                      p:[Double],originA:[Double],trialA:[Double],rows:[Row]) throws -> Correction {
        let size=factor.size,eps=NonlinearPrimalDual.epsilon,count=rows.count
        guard [masses,p,originA,trialA].allSatisfy({$0.count==size && $0.allSatisfy(\.isFinite)}),
              masses.allSatisfy({$0>=0}),entries.allSatisfy({(0..<size).contains($0.0) && (0..<size).contains($0.1) && $0.2.isFinite}),
              rows.allSatisfy({r in
                  r.jacobian.allSatisfy({(0..<size).contains($0.0) && $0.1.isFinite}) &&
                  [r.s,r.v,r.ps,r.pv,r.originB,r.trialB,r.originH,r.trialH].allSatisfy(\.isFinite) &&
                  (r.equalityVariable.map{(0..<size).contains($0) && masses[$0]==0} ?? (r.s>0 && r.v>0))
              }) else {throw RopePhysicsError.invalid("Invalid fullKKT defect input")}
        func product(_ x:[Double])->[Double] {
            var result=Array(repeating:0.0,count:size)
            for (i,j,value) in entries {
                result[i] += value*x[j]
                if i != j {result[j] += value*x[i]}
            }
            return result
        }
        var kp=product(p),ra=zip(trialA,originA).map(-)
        var rb=Array(repeating:0.0,count:count),rh=rb,rsv=rb,weights=rb,loads=rb
        for k in rows.indices {
            let row=rows[k],jp=row.jacobian.reduce(0.0){$0+$1.1*p[$1.0]}
            if let index=row.equalityVariable {
                rb[k]=row.trialB-row.originB-kp[index]
            } else {
                let diagonal=row.s/(row.v+eps*row.s)
                // Recover the complete Kp from its condensed representation.
                for (i,value) in row.jacobian {kp[i] -= value*(diagonal*jp+row.ps)}
                rh[k]=row.trialH-row.originH-(jp+eps*row.ps-row.pv)
                rsv[k]=(row.s+row.ps)*(row.v+row.pv)-row.s*row.v-(row.v*row.ps+row.s*row.pv)
                let elimination=try NonlinearPrimalDual.eliminate(s:row.s,v:row.v,h:rh[k],rc:-rsv[k])
                weights[k]=elimination.diagonal;loads[k]=elimination.load
            }
        }
        var rhs=Array(repeating:0.0,count:size)
        for i in masses.indices {
            if masses[i]>0 {ra[i] -= kp[i];rhs[i] = -ra[i]} else {ra[i]=0}
        }
        for k in rows.indices {
            if let index=rows[k].equalityVariable {rhs[index] = -rb[k]}
            else {for (i,value) in rows[k].jacobian {rhs[i] += value*loads[k]}}
        }
        // One extra RHS on the caller's unchanged factor; no alpha rescales e.
        let x=try factor.solve(rhs)
        var ds=Array(repeating:0.0,count:count),dv=ds,dl=ds,ke=product(x)
        var stationarity=0.0,equality=0.0,contact=0.0,complementarity=0.0
        for k in rows.indices {
            let row=rows[k],jx=row.jacobian.reduce(0.0){$0+$1.1*x[$1.0]}
            if let index=row.equalityVariable {
                dl[k]=x[index];equality=max(equality,abs(ke[index]+rb[k]))
            } else {
                ds[k]=loads[k]-weights[k]*jx;dv[k]=jx+eps*ds[k]+rh[k];dl[k] = -ds[k]
                for (i,value) in row.jacobian {ke[i] -= value*(weights[k]*jx+ds[k])}
                contact=max(contact,abs(jx+eps*ds[k]-dv[k]+rh[k]))
                complementarity=max(complementarity,abs(row.v*ds[k]+row.s*dv[k]+rsv[k]))
            }
        }
        for i in masses.indices where masses[i]>0 {stationarity=max(stationarity,abs(ke[i]+ra[i]))}
        guard [x,ds,dv,dl,ra,rb,rh,rsv].allSatisfy({$0.allSatisfy(\.isFinite)}),
              stationarity<=1e-10,equality<=1e-8,contact<=1e-10,complementarity<=1e-14 else {
            throw RopePhysicsError.invalid("Full recovered nonlinear defect equations failed")
        }
        return Correction(x:x,s:ds,v:dv,lambda:dl,remainderA:ra,remainderB:rb,remainderH:rh,remainderSV:rsv,
                          stationarity:stationarity,equality:equality,contact:contact,complementarity:complementarity)
    }
}
