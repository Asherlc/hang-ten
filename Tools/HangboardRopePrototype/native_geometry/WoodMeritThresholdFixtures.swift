import Foundation
import simd
let mesh=RopeCollisionMesh(vertices:[SIMD3(0,0,0),SIMD3(1,0,0),SIMD3(0,1,0),SIMD3(0,0,1)],
    triangles:[SIMD3(0,2,1),SIMD3(0,1,3),SIMD3(0,3,2),SIMD3(1,2,3)])
let collider=try RopeTriangleCollider(mesh:mesh)
var failures=0
func check(_ name:String,_ action:() throws -> Bool) {
    do {if try action(){print("PASS",name)}else{failures+=1;print("FAIL",name)}}
    catch {failures+=1;print("FAIL",name,error)}
}
check("whole link separated from root rejects before parity") {
    let a=SIMD3<Double>(-0.02,0.2,0.2),b=SIMD3<Double>(-0.02,0.4,0.2)
    return try collider.screenRootSeparated(from:a,to:b,radius:0.0036) &&
        collider.screenRootParityOutside(from:a,to:b) &&
        collider.segmentContacts(from:a,to:b,radius:0.0036).isEmpty &&
        collider.screenExactWoodContacts(from:a,to:b,radius:0.0036).isEmpty
}
check("clear endpoints cannot certify a root-crossing link") {
    try !collider.screenRootSeparated(from:SIMD3(-0.1,0.2,0.2),to:SIMD3(1.1,0.2,0.2),radius:0.0036)
}
check("inside endpoints and finite-radius uncertain links retain original penalty") {
    for (a,b) in [(SIMD3<Double>(0.2,0.2,0.2),SIMD3<Double>(0.3,0.2,0.2)),
        (SIMD3<Double>(-0.001,0.2,0.2),SIMD3<Double>(-0.002,0.4,0.2))] {
        guard try !collider.screenRootSeparated(from:a,to:b,radius:0.0036) else{return false}
        let original=collider.segmentContacts(from:a,to:b,radius:0.0036)
        let candidate=try collider.screenExactWoodContacts(from:a,to:b,radius:0.0036)
        guard !original.isEmpty,original.map(\.penetrationDepth)==candidate.map(\.penetrationDepth) else{return false}
    }
    return true
}
check("boundary uncertainty cannot reject a capsule") {
    let a=SIMD3<Double>(-0.00360000000000001,0.2,0.2)
    return try !collider.screenRootSeparated(from:a,to:a,radius:0.0036)
}
check("invalid finite and radius domains reject") {
    for radius in [Double.nan,0,-1,2] {
        do {_ = try collider.screenRootSeparated(from:.zero,to:.zero,radius:radius);return false} catch {}
    }
    do {_ = try collider.screenRootSeparated(from:SIMD3(.infinity,0,0),to:.zero,radius:0.0036);return false} catch {}
    return true
}
print("fixtures",5,"failures",failures)
exit(failures==0 ? 0:1)
