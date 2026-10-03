import Foundation
import simd

// Existing, unmodified all-contact solver only. No proposed bundle execution.
func box(_ a:SIMD3<Double>,_ b:SIMD3<Double>)->RopeCollisionMesh {
    let v=[SIMD3(a.x,a.y,a.z),SIMD3(b.x,a.y,a.z),SIMD3(b.x,b.y,a.z),SIMD3(a.x,b.y,a.z),
           SIMD3(a.x,a.y,b.z),SIMD3(b.x,a.y,b.z),SIMD3(b.x,b.y,b.z),SIMD3(a.x,b.y,b.z)]
    return RopeCollisionMesh(vertices:v,triangles:[SIMD3(0,2,1),SIMD3(0,3,2),SIMD3(4,5,6),SIMD3(4,6,7),
        SIMD3(0,1,5),SIMD3(0,5,4),SIMD3(1,2,6),SIMD3(1,6,5),SIMD3(2,3,7),SIMD3(2,7,6),SIMD3(3,0,4),SIMD3(3,4,7)])
}
let slabs=[box(SIMD3(-0.02,-0.02,-0.02),SIMD3(0,0.02,0.02)),
           box(SIMD3(0.001,-0.02,-0.02),SIMD3(0.02,0,0.02))]
var vertices:[SIMD3<Double>]=[],faces:[SIMD3<Int>]=[]
for slab in slabs {
    let offset=vertices.count;vertices += slab.vertices
    faces += slab.triangles.map{$0 &+ SIMD3(repeating:offset)}
}
let collider=try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:vertices,triangles:faces))
let a=SIMD3<Double>(0.00355,0.00355,-0.005),b=SIMD3<Double>(0.00355,0.00355,0.005)
let radius=0.0035,rowRadius=radius+RopeRegionGeometry.clearance+0.00005
let hits=collider.segmentContacts(from:a,to:b,radius:rowRadius)
precondition(hits.contains{$0.normal.x>0.999} && hits.contains{$0.normal.y>0.999})
// A rigidly translating capsule gives two in-plane variables; the board's
// shared height remains an independently coupled variable with mass five.
var system=try RopeBandedSystem(size:2,bandwidth:0)
try system.addSymmetric(row:0,column:0,value:1)
try system.addSymmetric(row:1,column:1,value:1)
let factor=try system.factorized(borderColumns:[[0,0]],borderMatrix:[[5]])
let rows=hits.map{hit in RopeLinearContact(indices:[0,1],coefficients:[hit.normal.x,hit.normal.y],
    border:[-hit.normal.y],residual:0.00005-hit.penetrationDepth)}
let result=try RopeContactSystem.solve(factor:factor,base:[-0.0002,-0.0002],border:[0],contacts:rows)
func clearance(_ base:[Double],_ height:Double)->Double {
    let relative=SIMD3(base[0],base[1]-height,0.0)
    return collider.segmentClearance(from:a+relative,to:b+relative)
}
let fullClearance=clearance(result.base,result.border[0])
precondition(fullClearance>=radius-0.00005)
precondition(result.border[0]<0 && result.base[1]<result.base[0])
// Independent original explicitly regularized KKT with both wall normals.
let x=rows.first{$0.coefficients[0]>0.999}!,y=rows.first{$0.coefficients[1]>0.999}!
let single=try RopeContactSystem.solve(factor:factor,base:[-0.0002,-0.0002],border:[0],contacts:[x])
let singleClearance=clearance(single.base,single.border[0])
precondition(singleClearance<radius-0.00005)
// The full solver's duplicate rows use separate regularizers; compare its own
// original equations, rather than assuming duplicate multipliers identical.
for row in rows {
    let gap=row.residual+row.coefficients[0]*result.base[0]+row.coefficients[1]*result.base[1]+row.border[0]*result.border[0]
    precondition(gap >= -1e-8)
}
let path=URL(fileURLWithPath:CommandLine.arguments[1]).appendingPathComponent("control.json")
let data:[String:Any]=["owner":"strong-owl-live-physics","originalSolverOnly":true,
    "originalRows":rows.count,"independentWallNormals":2,
    "capsuleRadiusMeters":radius,"physicalMinimumClearanceMeters":radius-0.00005,
    "fullClearanceMeters":fullClearance,"singleWallDiagnosticClearanceMeters":singleClearance,
    "sharedBoardHeightCorrectionMeters":result.border[0],"capsuleTranslationMeters":result.base,
    "fullGeometryPassed":true,"singleWallDiagnosticRejected":true,
    "candidateImplemented":false,"scope":"synthetic original-mesh/current-solver control; no trajectory or performance evidence"]
try JSONSerialization.data(withJSONObject:data,options:[.prettyPrinted,.sortedKeys]).write(to:path)
print("PASS original two-wall coupled control; single-wall diagnostic fails actual-mesh clearance")
