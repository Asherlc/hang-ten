import Foundation

enum BlockImpulse {
    static var diagnostics:[[String:Any]]=[]
    static var correctionCalls=0
    static var phases:[[String:Any]]=[]
    static func certifies(_ x:[Double],multipliers:[Double],contacts:[RopeLinearContact],size:Int)->Bool {
        guard x.allSatisfy({$0.isFinite}),multipliers.count==contacts.count,
              multipliers.allSatisfy({$0.isFinite && $0<=0}) else {return false}
        for (id,row) in contacts.enumerated() {
            var q=row.residual
            for k in row.indices.indices {q += row.coefficients[k]*x[row.indices[k]]}
            for k in row.border.indices {q += row.border[k]*x[size+k]}
            let gap=q-1e-8*multipliers[id]
            guard q.isFinite,gap.isFinite,q >= -1e-8,gap >= -1e-10,
                  abs(multipliers[id]*gap)<=1e-14 else {return false}
        }
        return true
    }
    static func solve(factor:RopeBandedFactorization,base:[Double],border:[Double],contacts:[RopeLinearContact],maxSweeps:Int=16,allowInexact:Bool=false) throws -> RopeContactSystem.Solution {
        let started=ProcessInfo.processInfo.systemUptime,size=base.count
        var x=base+border,multipliers=Array(repeating:0.0,count:contacts.count)
        var responses:[Int:[Double]]=[:],masses:[Int:Double]=[:]
        func dot(_ row:RopeLinearContact,_ vector:[Double])->Double {
            var value=0.0
            for k in row.indices.indices {value += row.coefficients[k]*vector[row.indices[k]]}
            for k in row.border.indices {value += row.border[k]*vector[size+k]}
            return value
        }
        var gapError=Double.infinity,complementarity=Double.infinity,worstQ=Double.infinity
        for sweep in 0..<maxSweeps {
            for (id,row) in contacts.enumerated() {
                let q=row.residual+dot(row,x)
                if q>=0 && multipliers[id]==0 {continue}
                if responses[id] == nil {
                    var load=Array(repeating:0.0,count:size)
                    for k in row.indices.indices {load[row.indices[k]] += row.coefficients[k]}
                    let solved=try factor.solve(rhs:load,borderRHS:row.border)
                    let response=solved.base+solved.border
                    let mass=dot(row,response)+1e-8
                    guard mass>0,mass.isFinite else {throw RopePhysicsError.invalid("Nonpositive block response")}
                    guard (responses.count+1)*x.count<=8_000_000 else {throw RopePhysicsError.invalid("Block response storage bound")}
                    responses[id]=response;masses[id]=mass
                }
                let next=min(0,multipliers[id]+(q-1e-8*multipliers[id])/masses[id]!)
                let delta=next-multipliers[id]
                for i in x.indices {x[i] -= responses[id]![i]*delta}
                multipliers[id]=next
            }
            gapError=0;complementarity=0;worstQ=0
            for (id,row) in contacts.enumerated() {
                let q=row.residual+dot(row,x),gap=q-1e-8*multipliers[id]
                worstQ=min(worstQ,q)
                gapError=max(gapError,max(0,-gap))
                complementarity=max(complementarity,abs(multipliers[id]*gap))
            }
            if worstQ >= -1e-8 && gapError<=1e-10 && complementarity<=1e-14 {
                // Reconstruct once from the original factor responses, rather
                // than accepting accumulation drift in the impulse sweeps.
                x=base+border
                for id in responses.keys.sorted() {for i in x.indices {x[i] -= responses[id]![i]*multipliers[id]}}
                guard certifies(x,multipliers:multipliers,contacts:contacts,size:size) else {throw RopePhysicsError.invalid("Recovered block contact certificate failed")}
                worstQ=0;gapError=0;complementarity=0
                for (id,row) in contacts.enumerated() {
                    let q=row.residual+dot(row,x),gap=q-1e-8*multipliers[id]
                    worstQ=min(worstQ,q);gapError=max(gapError,max(0,-gap))
                    complementarity=max(complementarity,abs(multipliers[id]*gap))
                }
                let allQ=contacts.map{$0.residual+dot($0,x)}
                let allGaps=allQ.indices.map{allQ[$0]-1e-8*multipliers[$0]}
                diagnostics.append(["affineResiduals":allQ,"regularizedGaps":allGaps,"multipliers":multipliers,"sweeps":sweep+1,"rows":contacts.count,"responses":responses.count,"seconds":ProcessInfo.processInfo.systemUptime-started,"gapError":gapError,"complementarity":complementarity,"minimumQ":worstQ,"passed":true])
                return RopeContactSystem.Solution(base:Array(x.prefix(size)),border:Array(x.dropFirst(size)),multipliers:multipliers,activeIDs:multipliers.indices.filter{multipliers[$0]<0})
            }
        }
        if allowInexact {
            x=base+border
            for id in responses.keys.sorted() {for i in x.indices {x[i] -= responses[id]![i]*multipliers[id]}}
            guard x.allSatisfy({$0.isFinite}),multipliers.allSatisfy({$0.isFinite && $0<=0}) else {
                throw RopePhysicsError.invalid("Invalid inexact block proposal")
            }
            let q=contacts.map{$0.residual+dot($0,x)}
            let gaps=q.indices.map{q[$0]-1e-8*multipliers[$0]}
            guard (q+gaps).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite inexact residual")}
            gapError=gaps.map{max(0,-$0)}.max() ?? 0
            worstQ=min(0,q.min() ?? 0)
            complementarity=gaps.indices.map{abs(gaps[$0]*multipliers[$0])}.max() ?? 0
            diagnostics.append(["sweeps":maxSweeps,"rows":contacts.count,"responses":responses.count,"seconds":ProcessInfo.processInfo.systemUptime-started,"gapError":gapError,"complementarity":complementarity,"minimumQ":worstQ,"passed":certifies(x,multipliers:multipliers,contacts:contacts,size:size),"inexactProposal":true,"affineResiduals":q,"regularizedGaps":gaps,"multipliers":multipliers])
            return RopeContactSystem.Solution(base:Array(x.prefix(size)),border:Array(x.dropFirst(size)),multipliers:multipliers,activeIDs:multipliers.indices.filter{multipliers[$0]<0})
        }
        diagnostics.append(["sweeps":maxSweeps,"rows":contacts.count,"responses":responses.count,"seconds":ProcessInfo.processInfo.systemUptime-started,"gapError":gapError,"complementarity":complementarity,"minimumQ":worstQ,"passed":false])
        throw RopePhysicsError.invalid("Bounded block impulse exhausted")
    }
}
