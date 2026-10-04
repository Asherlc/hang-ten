import Foundation
import simd
extension WoodMajorizer {
    static func selectedBlock(_ selection:Selection,a:[SIMD3<Double>],b:[SIMD3<Double>])->Block? {
        func block(_ candidate:WoodMajorizer.Candidate)->WoodMajorizer.Block? {
                guard let pair=candidate.pair,pair.ropeClamp=="free",candidate.boundaries.isEmpty,
                    ["interior","triangleStart","triangleEnd"].contains(pair.ropeFormula),
                    let edge=Int(candidate.name.dropFirst(4)),(0..<3).contains(edge) else{return nil}
                var unit:SIMD3<Double>?=nil
                if pair.triangleFormula=="projected" {
                    let u=selection.triangle[(edge+1)%3]-selection.triangle[edge],ee=simd_length_squared(u)
                    guard ee>0 else{return nil}
                    let t=simd_dot(candidate.surface-selection.triangle[edge],u)/ee
                    guard t>0,t<1 else{return nil};unit=u/sqrt(ee)
                }else if pair.triangleFormula != "zero" && pair.triangleFormula != "one" {return nil}
                return WoodMajorizer.block(start:selection.start,end:selection.end,point:candidate.point,surface:candidate.surface,fraction:candidate.fraction,
                    edgeUnit:unit,startSeeds:a,endSeeds:b)
            }
            guard let w=block(selection.candidates[selection.winner]) else{return nil}
            // A tied branch is allowed only when its complete rank block agrees exactly.
            var common=true
            for index in selection.ties {
                guard let other=block(selection.candidates[index]) else{common=false;break}
                for j in w.vector.indices {for k in w.vector.indices {
                    if w.vector[j]*w.vector[k]/w.denominator != other.vector[j]*other.vector[k]/other.denominator {common=false}
                }}
            }
            guard common else{return nil}
        return w
    }
}
