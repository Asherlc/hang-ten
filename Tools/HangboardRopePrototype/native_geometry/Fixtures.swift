import Foundation
import simd

let vertices: [SIMD3<Double>] = [SIMD3(0,0,0), SIMD3(1,0,0), SIMD3(0,1,0), SIMD3(0,0,1)]
let mesh = RopeCollisionMesh(vertices: vertices, triangles: [SIMD3(0,2,1),SIMD3(0,1,3),SIMD3(0,3,2),SIMD3(1,2,3)])
let collider = try RopeTriangleCollider(mesh: mesh)
let tree = try collider.screenTree()
let stream = try BVHStream(nodes: tree.0, faces: tree.1, triangles: tree.2)
let points: [[SIMD3<Double>]] = [[SIMD3(-0.001,0.2,0.2)], [SIMD3(2,2,2)], [SIMD3(-0.1,0.3,0.3),SIMD3(1.1,0.3,0.3)], [SIMD3(0,0,0)]]
let queries = try points.map { try BVHQuery($0, 0.0035) }
let actual = try stream.candidates(queries)
let expected = queries.map { q in tree.2.indices.filter { integerIntersects(tree.2[$0],q) } }
guard actual == expected else { print("FAIL GPU BVH omits or adds integer candidates: \(actual) != \(expected)"); exit(1) }
print("PASS tetrahedron clear, overlapping, whole-segment and vertex candidates")
do { _ = try BVHQuery([SIMD3(100,0,0)], 0.0035); print("FAIL range guard"); exit(1) }
catch { print("PASS bounded integer arithmetic rejects unsafe input") }
var manyVertices: [SIMD3<Double>] = [], manyFaces: [SIMD3<Int>] = []
for i in 0..<6 {
    let offset = manyVertices.count
    manyVertices += vertices.map { $0 * 0.01 + SIMD3(Double(i)*0.03,0,0) }
    manyFaces += mesh.triangles.map { $0 &+ SIMD3<Int>(repeating:offset) }
}
let manyCollider = try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:manyVertices,triangles:manyFaces))
let manyTree = try manyCollider.screenTree()
let manyStream = try BVHStream(nodes:manyTree.0,faces:manyTree.1,triangles:manyTree.2)
let manyPoints: [[SIMD3<Double>]] = [[SIMD3(-0.002,0.003,0.003),SIMD3(0.17,0.003,0.003)], [SIMD3(0.001,0.001,0.001),SIMD3(0.002,0.001,0.001)], [SIMD3(0,0,0),SIMD3(0,0,0)]]
let manyQueries = try manyPoints.map { try BVHQuery($0,0.0035) }
let manyActual = try manyStream.candidates(manyQueries)
for i in manyQueries.indices {
    let expected = manyTree.2.indices.filter { integerIntersects(manyTree.2[$0],manyQueries[i]) }
    guard expected == manyActual[i] else { print("FAIL multi-leaf traversal"); exit(1) }
    let points = manyPoints[i], reference = manyCollider.segmentContacts(from:points[0],to:points[1],radius:0.0035)
    let actual = manyCollider.screenSegmentContacts(from:points[0],to:points[1],radius:0.0035,faces:manyActual[i])
    guard actual.count == reference.count, zip(actual,reference).allSatisfy({a,b in
        a.centerlinePoint == b.centerlinePoint && a.surfacePoint == b.surfacePoint && a.normal == b.normal && a.fraction == b.fraction && a.penetrationDepth == b.penetrationDepth
    }) else { print("FAIL exact witness, normal or inside fallback"); exit(1) }
}
print("PASS multi-leaf compact emission and exact whole-segment/inside/vertex witnesses")
var cyclic = manyTree.0; cyclic[0].links.x = 0
do { _ = try BVHStream(nodes:cyclic,faces:manyTree.1,triangles:manyTree.2); print("FAIL cyclic tree guard"); exit(1) }
catch { print("PASS cyclic traversal rejected before GPU submission") }
var omitted = tree.0; omitted[0].links.w -= 1
do { _ = try BVHStream(nodes:omitted,faces:tree.1,triangles:tree.2); print("FAIL omitted leaf facet guard"); exit(1) }
catch { print("PASS every source facet must belong to exactly one leaf") }
let bounds = tree.0[0].bounds
let overlapping = [BVHNode(bounds:bounds,links:SIMD4(1,2,0,0)),
                   BVHNode(bounds:bounds,links:SIMD4(-1,-1,0,2)),
                   BVHNode(bounds:bounds,links:SIMD4(-1,-1,1,2))]
do { _ = try BVHStream(nodes:overlapping,faces:tree.1,triangles:tree.2); print("FAIL overlapping leaf guard"); exit(1) }
catch { print("PASS overlapping leaf intervals are rejected") }
