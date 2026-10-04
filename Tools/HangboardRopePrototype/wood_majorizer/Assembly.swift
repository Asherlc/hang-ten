import Foundation
// Native only: add the complete rank-one update once; no multiplier/equality slot changed.
enum WoodMajorizerAssembly {
    static func add(system:inout RopeBandedSystem,columns:inout [[Double]],border:inout [[Double]],
        indices:[Int],values:[Double],height:Double,scale:Double)throws {
        for a in indices.indices {
            for j in 0...a {try system.addSymmetric(row:indices[a],column:indices[j],value:scale*values[a]*values[j])}
            columns[0][indices[a]] += scale*values[a]*height
        }
        border[0][0] += scale*height*height
    }
}
func majorizerIntegrationFixtures()throws {
    // Independent closed form: solve D+k vvT by Sherman-Morrison.
    // Base slot1 stands in for an unaffected equality/layout slot; height is border slot0.
    var system=try RopeBandedSystem(size:3,bandwidth:2)
    let diagonal=[2.0,7,3,5],v=[-1.0,0,2,3],rhs=[1.0,9,-2,4],k=0.7
    for i in 0..<3 {try system.addSymmetric(row:i,column:i,value:diagonal[i])}
    var columns=[[0.0,0,0]],border=[[5.0]]
    try WoodMajorizerAssembly.add(system:&system,columns:&columns,border:&border,indices:[0,2],values:[-1,2],height:3,scale:k)
    let solved=try system.factorized(borderColumns:columns,borderMatrix:border).solve(rhs:Array(rhs.prefix(3)),borderRHS:[rhs[3]])
    let dot=zip(v,rhs).enumerated().reduce(0.0){$0+$1.element.0*$1.element.1/diagonal[$1.offset]}
    let denominator=1+k*v.indices.reduce(0.0){$0+v[$1]*v[$1]/diagonal[$1]}
    let expected=v.indices.map{rhs[$0]/diagonal[$0]-k*v[$0]/diagonal[$0]*dot/denominator}
    guard zip(solved.base+solved.border,expected).allSatisfy({abs($0-$1)<1e-12}),abs(columns[0][0]+2.1)<1e-14,abs(columns[0][2]-4.2)<1e-14 else {
        throw RopePhysicsError.invalid("dense mixed-height rank-one assembly")
    }
    let a=SIMD3<Double>(-1,-0.7,0.0036),b=SIMD3<Double>(1,-0.7,0.0036)
    let triangle=[SIMD3<Double>(0,0,0),SIMD3(1,1,0),SIMD3(-1,1,0)]
    let selection=try RopeTriangleCollider.majorizerWoodSelection(a,b,triangle)
    let seedsA=[SIMD3<Double>(0,0,1)],seedsB=[SIMD3<Double>.zero]
    guard !selection.ties.isEmpty,WoodMajorizer.selectedBlock(selection,a:seedsA,b:seedsB) != nil else {
        throw RopePhysicsError.invalid("common vertex tie selection")
    }
    // Actual classifier detection of an exact raw closest-parameter boundary.
    let nativeBoundary=try RopeTriangleCollider.majorizerWoodSelection(SIMD3(-1,-1,0.0036),SIMD3(1,-1,0.0036),triangle)
    guard !nativeBoundary.candidates[nativeBoundary.winner].boundaries.isEmpty,
        WoodMajorizer.selectedBlock(nativeBoundary,a:seedsA,b:seedsB)==nil else {throw RopePhysicsError.invalid("native boundary detection fallback")}
    // Explicit boundary metadata must select original H even with a valid scalar block.
    var candidates=selection.candidates
    let win=selection.winner,c=candidates[win]
    candidates[win] = .init(name:c.name,point:c.point,surface:c.surface,fraction:c.fraction,region:c.region,pair:c.pair,boundaries:["triangleClampBoundary"])
    let boundary=WoodMajorizer.Selection(start:a,end:b,triangle:triangle,candidates:candidates,winner:win,ties:selection.ties)
    guard WoodMajorizer.selectedBlock(boundary,a:seedsA,b:seedsB)==nil else {throw RopePhysicsError.invalid("boundary fallback")}
    let endpoint=try RopeTriangleCollider.majorizerWoodSelection(SIMD3(2,-1,0.0036),SIMD3(3,-1,0.0036),triangle)
    guard WoodMajorizer.selectedBlock(endpoint,a:seedsA,b:seedsB)==nil else {throw RopePhysicsError.invalid("selected endpoint fallback")}
}
