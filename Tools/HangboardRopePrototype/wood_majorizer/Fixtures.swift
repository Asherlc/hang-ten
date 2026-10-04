import Foundation
import simd
func majorizerFixtures()throws {
    func demand(_ b:Bool,_ message:String)throws {if !b {throw NSError(domain:message,code:1)}}
    // Unit rope x-axis at z=d above a vertex; closest fraction is interior.
    // b = n·(B-A) gives [-1,+1] for endpoint-z seeds. Omitting it yields zero.
    let a=SIMD3<Double>(-1,0,2),z=SIMD3<Double>(1,0,2),p=SIMD3<Double>(0,0,2)
    let seedsA=[SIMD3<Double>(0,0,1),.zero,SIMD3<Double>(0,0,-1)]
    let seedsB=[SIMD3<Double>.zero,SIMD3<Double>(0,0,1),SIMD3<Double>(0,0,-1)]
    guard let v=WoodMajorizer.block(start:a,end:z,point:p,surface:.zero,fraction:0.5,edgeUnit:nil,startSeeds:seedsA,endSeeds:seedsB) else {throw NSError(domain:"missing vertex majorizer",code:1)}
    try demand(v.vector == [-1,1,0] && v.denominator==2,"vertex moving-fraction term")
    // x-directed rope over a y-directed triangle edge gives the same positive Schur term.
    guard let e=WoodMajorizer.block(start:a,end:z,point:p,surface:.zero,fraction:0.5,edgeUnit:SIMD3(0,1,0),startSeeds:seedsA,endSeeds:seedsB) else {throw NSError(domain:"missing edge majorizer",code:1)}
    try demand(e.vector == [-1,1,0] && e.denominator==2,"static edge elimination")
    // Height moves the nonattached endpoint only: n·E creates a height cross block.
    let mixed=WoodMajorizer.block(start:a,end:z,point:p,surface:.zero,fraction:0.5,edgeUnit:nil,startSeeds:[SIMD3(0,0,1),SIMD3(0,0,-1)],endSeeds:[.zero,.zero])!
    try demand(mixed.vector == [-1,1],"attached height seed")
    // Oblique rope: eliminating static y-motion must remove its y contribution.
    let oa=SIMD3<Double>(-1,-0.5,2),ob=SIMD3<Double>(1,0.5,2)
    let oy=[SIMD3<Double>(0,1,0)],oz=[SIMD3<Double>.zero]
    let ov=WoodMajorizer.block(start:oa,end:ob,point:p,surface:.zero,fraction:0.5,edgeUnit:nil,startSeeds:oy,endSeeds:oz)!
    let oe=WoodMajorizer.block(start:oa,end:ob,point:p,surface:.zero,fraction:0.5,edgeUnit:SIMD3(0,1,0),startSeeds:oy,endSeeds:oz)!
    try demand(ov.vector==[0.25] && ov.denominator==2.5 && oe.vector==[0] && oe.denominator==2,"oblique static-edge elimination")
    let common=WoodMajorizer.block(start:a,end:z,point:p,surface:.zero,fraction:0.5,edgeUnit:nil,startSeeds:[SIMD3(-1,0,0)],endSeeds:[SIMD3(-1,0,0)])!
    try demand(common.vector==[-1] && common.denominator==2,"shared tangential height")
    for x in [[1.0,2,3],[-4,2,0],[0,0,1]] {let dot=zip(v.vector,x).reduce(0.0){$0+$1.0*$1.1};try demand(dot*dot/v.denominator>=0,"PSD")}
    try demand(WoodMajorizer.block(start:a,end:z,point:a,surface:.zero,fraction:0,edgeUnit:nil,startSeeds:seedsA,endSeeds:seedsB)==nil,"clamped endpoint fallback")
    try demand(WoodMajorizer.block(start:a,end:z,point:p,surface:.zero,fraction:0.5,edgeUnit:SIMD3(1,0,0),startSeeds:seedsA,endSeeds:seedsB)==nil,"parallel fallback")
}
