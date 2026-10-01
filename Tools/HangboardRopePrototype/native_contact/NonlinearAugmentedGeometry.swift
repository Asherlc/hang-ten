// Appended to a fresh collider snapshot, so the exact existing primitives
// remain authoritative. Not compiled into the app.
extension RopeTriangleCollider {
    func augmentedContains(_ point:SIMD3<Double>)->Bool {contains(point)}
    static func augmentedNondegenerateTriangle(_ start:SIMD3<Double>,_ end:SIMD3<Double>,
        _ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>) throws -> (distance:Double,normal:SIMD3<Double>,fraction:Double) {
        let hit=augmentedTriangle(start,end,a,b,c)
        guard hit.distance>1e-10 else {throw RopePhysicsError.invalid("Degenerate or intersecting nonlinear wood feature")}
        return hit
    }
    static func augmentedTriangle(_ start:SIMD3<Double>,_ end:SIMD3<Double>,
        _ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>)->(distance:Double,normal:SIMD3<Double>,fraction:Double) {
        var best=Double.infinity,p=start,q=a,f=0.0
        func consider(_ first:SIMD3<Double>,_ second:SIMD3<Double>,_ fraction:Double) {
            let square=simd_length_squared(first-second)
            if square<best {best=square;p=first;q=second;f=fraction}
        }
        consider(start,Self.triangleClosest(start,a,b,c),0)
        if start != end {
            consider(end,Self.triangleClosest(end,a,b,c),1)
            if let t=Self.rayTriangle(start,end-start,a,b,c),t>=0,t<=1 {
                let point=start+(end-start)*t;consider(point,point,t)
            }
            for edge in [(a,b),(b,c),(c,a)] {
                let pair=Self.segmentPair(start,end,edge.0,edge.1);consider(pair.0,pair.1,pair.2)
            }
        }
        let distance=sqrt(best)
        return (distance,distance>1e-10 ? (p-q)/distance:simd_normalize(simd_cross(b-a,c-a)),f)
    }
}
