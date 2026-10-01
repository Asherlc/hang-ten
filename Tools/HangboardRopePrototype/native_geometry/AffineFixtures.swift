import Foundation
import simd

let vertices: [SIMD3<Double>] = [SIMD3(0,0,0),SIMD3(1,0,0),SIMD3(0,1,0),SIMD3(0,0,1)]
let mesh = RopeCollisionMesh(vertices:vertices,triangles:[SIMD3(0,2,1),SIMD3(0,1,3),SIMD3(0,3,2),SIMD3(1,2,3)])
let collider = try RopeTriangleCollider(mesh:mesh)
var failures = 0
func check(_ name: String, _ action: () throws -> Bool) {
    do { if try action() {print("PASS",name)} else {failures += 1;print("FAIL",name)} }
    catch {failures += 1;print("FAIL",name,error)}
}
let regions = ProcessInfo.processInfo.environment["HANGTEN_AFFINE_GEOMETRY_METHOD"] == "regions"
let fast = ProcessInfo.processInfo.environment["HANGTEN_AFFINE_FAST_BOXES"] == "1"
let slabs = ProcessInfo.processInfo.environment["HANGTEN_AFFINE_SLABS"] == "1" ? collider.affineSlabIndex():nil
func screen(from start: SIMD3<Double>,to end: SIMD3<Double>,requiredClearance: Double,
            startCorrection: SIMD3<Double>,endCorrection: SIMD3<Double>,thresholdRegions: Bool,fastRegionBoxes: Bool) throws -> Bool {
    if let slabs {return try slabs.screenAffinelyClear(from:start,to:end,requiredClearance:requiredClearance,
        startCorrection:startCorrection,endCorrection:endCorrection)}
    return try collider.screenAffinelyClear(from:start,to:end,requiredClearance:requiredClearance,
        startCorrection:startCorrection,endCorrection:endCorrection,thresholdRegions:thresholdRegions,fastRegionBoxes:fastRegionBoxes)
}
let zero = SIMD3<Double>.zero
let near = SIMD3<Double>(-0.01,0.2,0.2)
// Hand-checked 10 mm distance to x=0; the finite-radius gap is 6.5 mm.
// A false default, omitted movement, unsigned sign or endpoint-only distance
// would respectively fail these clear, inward, inside and crossing cases.
check("clear point supports every frozen unit normal") {
    try screen(from:near,to:near,requiredClearance:0.0035,
        startCorrection:SIMD3(0.001,0,0),endCorrection:SIMD3(0.001,0,0),thresholdRegions:regions,fastRegionBoxes:fast)
}
check("inward correction invalidates original affine bound") {
    try !screen(from:near,to:near,requiredClearance:0.0035,
        startCorrection:SIMD3(0.007,0,0),endCorrection:SIMD3(0.007,0,0),thresholdRegions:regions,fastRegionBoxes:fast)
}
check("inside original geometry cannot use positive unsigned distance") {
    let p = SIMD3<Double>(0.2,0.2,0.2)
    return try !screen(from:p,to:p,requiredClearance:0.0035,startCorrection:zero,endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
}
check("whole segment crossing blocks proof despite clear endpoints") {
    try !screen(from:SIMD3(-0.1,0.2,0.2),to:SIMD3(1.1,0.2,0.2),
        requiredClearance:0.0035,startCorrection:zero,endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
}
check("clear whole segment bounds all original material fractions") {
    try screen(from:near,to:SIMD3(-0.01,0.4,0.2),requiredClearance:0.0035,
        startCorrection:SIMD3(0.001,0,0),endCorrection:SIMD3(0,0.002,0),thresholdRegions:regions,fastRegionBoxes:fast)
}
check("threshold uncertainty falls back rather than omitting a facet") {
    let p = SIMD3<Double>(-0.0035,0.2,0.2)
    return try !screen(from:p,to:p,requiredClearance:0.0035,startCorrection:zero,endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
}
check("invalid input rejects before a geometry certificate") {
    do {
        _ = try screen(from:near,to:near,requiredClearance:0.0035,
            startCorrection:SIMD3(.nan,0,0),endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
        return false
    } catch {return true}
}
// This independently evaluates every original manifold row, rather than
// checking nonlinear clearance only at a moved endpoint. Surface selection and
// deduplication remain the original collider's authority.
check("certified point retains every original affine inequality") {
    let correction = SIMD3<Double>(0.002,0.001,-0.001)
    guard try screen(from:near,to:near,requiredClearance:0.0035,
        startCorrection:correction,endCorrection:correction,thresholdRegions:regions,fastRegionBoxes:fast) else {return false}
    let contacts = collider.segmentContacts(from:near,to:near,radius:0.012)
    return !contacts.isEmpty && contacts.allSatisfy {
        0.012-$0.penetrationDepth-0.0035+simd_dot($0.normal,correction) >= -1e-10
    }
}
check("oblique slab proves separation that its axis-aligned box cannot") {
    let triangle = [SIMD3<Double>(0,0,0),SIMD3(1,0,1),SIMD3(0,1,1)]
    let axis = simd_normalize(SIMD3<Double>(-1,-1,1))
    let center = SIMD3<Double>(0.25,0.25,0.5)
    let p = center+axis*0.01
    let slab = RopeAffineSlab(vertices:triangle,axis:axis)
    let bound = slab.lowerBound(from:p,to:p+SIMD3(0.001,-0.001,0))
    return bound > 0.009999999 && bound <= 0.01
}
check("slab crossing and boundary retain zero lower bound") {
    let triangle = [SIMD3<Double>(0,0,0),SIMD3(1,0,1),SIMD3(0,1,1)]
    let axis = simd_normalize(SIMD3<Double>(-1,-1,1)),center = SIMD3<Double>(0.25,0.25,0.5)
    let slab = RopeAffineSlab(vertices:triangle,axis:axis)
    return slab.lowerBound(from:center-axis*0.01,to:center+axis*0.01)==0 && slab.lowerBound(from:center,to:center)==0
}
check("zero slab direction conservatively supplies no certificate") {
    RopeAffineSlab(vertices:vertices,axis:zero).lowerBound(from:near,to:near)==0
}
check("batch preserves original inside, inward and whole-segment crossing decisions") {
    let index = collider.affineSlabIndex()
    let cases = [
        RopeAffineQuery(start:near,end:near,requiredClearance:0.0035,startCorrection:zero,endCorrection:zero),
        RopeAffineQuery(start:near,end:near,requiredClearance:0.0035,startCorrection:SIMD3(0.007,0,0),endCorrection:zero),
        RopeAffineQuery(start:SIMD3(0.2,0.2,0.2),end:SIMD3(0.2,0.2,0.2),requiredClearance:0.0035,startCorrection:zero,endCorrection:zero),
        RopeAffineQuery(start:SIMD3(-0.1,0.2,0.2),end:SIMD3(1.1,0.2,0.2),requiredClearance:0.0035,startCorrection:zero,endCorrection:zero),
        RopeAffineQuery(start:near,end:SIMD3(-0.01,0.4,0.2),requiredClearance:0.0035,startCorrection:zero,endCorrection:zero)]
    return try index.screenBatch(cases) == [true,false,false,false,true]
}
check("batch handles empty input and rejects a nonfinite proof domain") {
    let index = collider.affineSlabIndex()
    guard try index.screenBatch([]).isEmpty else {return false}
    do {
        _ = try index.screenBatch([RopeAffineQuery(start:near,end:near,requiredClearance:0.0035,
            startCorrection:SIMD3(.nan,0,0),endCorrection:zero)])
        return false
    } catch {return true}
}
check("dual hierarchy decisions retain original cube geometry authority") {
    let points: [SIMD3<Double>] = [SIMD3(0,0,0),SIMD3(1,0,0),SIMD3(1,1,0),SIMD3(0,1,0),
        SIMD3(0,0,1),SIMD3(1,0,1),SIMD3(1,1,1),SIMD3(0,1,1)]
    let cube = try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:points,triangles:[
        SIMD3(0,2,1),SIMD3(0,3,2),SIMD3(4,5,6),SIMD3(4,6,7),
        SIMD3(0,1,5),SIMD3(0,5,4),SIMD3(3,7,6),SIMD3(3,6,2),
        SIMD3(0,4,7),SIMD3(0,7,3),SIMD3(1,2,6),SIMD3(1,6,5)]))
    let index = cube.affineSlabIndex()
    var inputs: [RopeAffineQuery] = []
    for x in [-0.2,0.2,0.7,1.2] {for y in [-0.2,0.2,0.7,1.2] {for z in [-0.2,0.2,0.7,1.2] {
        let start = SIMD3<Double>(x,y,z)
        inputs.append(RopeAffineQuery(start:start,end:start,requiredClearance:0.05,startCorrection:zero,endCorrection:zero))
        inputs.append(RopeAffineQuery(start:start,end:start+SIMD3(0.5,-0.5,0.1),requiredClearance:0.05,
            startCorrection:SIMD3(0.01,0,0),endCorrection:SIMD3(0,0.02,0)))
    }}}
    let actual = try index.screenBatch(inputs)
    let expected = try inputs.map {q in try cube.screenAffinelyClear(from:q.start,to:q.end,
        requiredClearance:q.requiredClearance,startCorrection:q.startCorrection,endCorrection:q.endCorrection)}
    return actual == expected && actual.contains(true) && actual.contains(false)
}
print("fixtures",14,"failures",failures)
exit(failures == 0 ? 0:1)
