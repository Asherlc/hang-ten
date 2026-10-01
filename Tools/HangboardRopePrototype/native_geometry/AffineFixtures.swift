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
let zero = SIMD3<Double>.zero
let near = SIMD3<Double>(-0.01,0.2,0.2)
// Hand-checked 10 mm distance to x=0; the finite-radius gap is 6.5 mm.
// A false default, omitted movement, unsigned sign or endpoint-only distance
// would respectively fail these clear, inward, inside and crossing cases.
check("clear point supports every frozen unit normal") {
    try collider.screenAffinelyClear(from:near,to:near,requiredClearance:0.0035,
        startCorrection:SIMD3(0.001,0,0),endCorrection:SIMD3(0.001,0,0),thresholdRegions:regions,fastRegionBoxes:fast)
}
check("inward correction invalidates original affine bound") {
    try !collider.screenAffinelyClear(from:near,to:near,requiredClearance:0.0035,
        startCorrection:SIMD3(0.007,0,0),endCorrection:SIMD3(0.007,0,0),thresholdRegions:regions,fastRegionBoxes:fast)
}
check("inside original geometry cannot use positive unsigned distance") {
    let p = SIMD3<Double>(0.2,0.2,0.2)
    return try !collider.screenAffinelyClear(from:p,to:p,requiredClearance:0.0035,startCorrection:zero,endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
}
check("whole segment crossing blocks proof despite clear endpoints") {
    try !collider.screenAffinelyClear(from:SIMD3(-0.1,0.2,0.2),to:SIMD3(1.1,0.2,0.2),
        requiredClearance:0.0035,startCorrection:zero,endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
}
check("clear whole segment bounds all original material fractions") {
    try collider.screenAffinelyClear(from:near,to:SIMD3(-0.01,0.4,0.2),requiredClearance:0.0035,
        startCorrection:SIMD3(0.001,0,0),endCorrection:SIMD3(0,0.002,0),thresholdRegions:regions,fastRegionBoxes:fast)
}
check("threshold uncertainty falls back rather than omitting a facet") {
    let p = SIMD3<Double>(-0.0035,0.2,0.2)
    return try !collider.screenAffinelyClear(from:p,to:p,requiredClearance:0.0035,startCorrection:zero,endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
}
check("invalid input rejects before a geometry certificate") {
    do {
        _ = try collider.screenAffinelyClear(from:near,to:near,requiredClearance:0.0035,
            startCorrection:SIMD3(.nan,0,0),endCorrection:zero,thresholdRegions:regions,fastRegionBoxes:fast)
        return false
    } catch {return true}
}
// This independently evaluates every original manifold row, rather than
// checking nonlinear clearance only at a moved endpoint. Surface selection and
// deduplication remain the original collider's authority.
check("certified point retains every original affine inequality") {
    let correction = SIMD3<Double>(0.002,0.001,-0.001)
    guard try collider.screenAffinelyClear(from:near,to:near,requiredClearance:0.0035,
        startCorrection:correction,endCorrection:correction,thresholdRegions:regions,fastRegionBoxes:fast) else {return false}
    let contacts = collider.segmentContacts(from:near,to:near,radius:0.012)
    return !contacts.isEmpty && contacts.allSatisfy {
        0.012-$0.penetrationDepth-0.0035+simd_dot($0.normal,correction) >= -1e-10
    }
}
print("fixtures",8,"failures",failures)
exit(failures == 0 ? 0:1)
