import Foundation
import simd
// Isolated native screen only. Generalized coordinates: endpoint xyz and shared height.
enum WoodMajorizer {
    struct PairBranch {let ropeFormula:String;let ropeClamp:String;let triangleFormula:String;var boundaries:[String]=[]}
    struct Candidate {
        let name:String
        let point:SIMD3<Double>
        let surface:SIMD3<Double>
        let fraction:Double
        let region:String
        let pair:PairBranch?
        var boundaries:[String]=[]
    }
    struct Selection {let start:SIMD3<Double>;let end:SIMD3<Double>;let triangle:[SIMD3<Double>];let candidates:[Candidate];let winner:Int;let ties:[Int]}
    struct Block { let vector:[Double];let denominator:Double }
    static func block(start:SIMD3<Double>,end:SIMD3<Double>,point:SIMD3<Double>,surface:SIMD3<Double>,fraction:Double,edgeUnit:SIMD3<Double>?,startSeeds:[SIMD3<Double>],endSeeds:[SIMD3<Double>])->Block? {
        guard fraction>0,fraction<1,startSeeds.count==endSeeds.count,(1...7).contains(startSeeds.count) else{return nil}
        let delta=point-surface,d=simd_length(delta),e=end-start
        guard d>1e-10,d.isFinite,simd_length(e)>0 else{return nil}
        let n=delta/d
        guard abs(simd_dot(n,e))/simd_length(e)<=1e-10 else{return nil}
        if let u=edgeUnit {guard abs(simd_length(u)-1)<=1e-12,abs(simd_dot(n,u))<=1e-10 else{return nil}}
        func project(_ v:SIMD3<Double>)->SIMD3<Double> {
            let p=edgeUnit.map{v-$0*simd_dot($0,v)} ?? v
            return (p-n*simd_dot(n,v))/d
        }
        let we=project(e),c=simd_dot(e,we)
        guard c>0,c.isFinite else{return nil}
        var b:[Double]=[]
        for i in startSeeds.indices {
            let l=startSeeds[i]*(1-fraction)+endSeeds[i]*fraction
            b.append(simd_dot(l,we)+simd_dot(n,endSeeds[i]-startSeeds[i]))
        }
        guard b.allSatisfy({$0.isFinite}),b.allSatisfy({x in b.allSatisfy{(x*$0/c).isFinite}}) else{return nil}
        return Block(vector:b,denominator:c)
    }
}
