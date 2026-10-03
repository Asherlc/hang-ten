// IEEE round-to-nearest addition/multiplication are monotone. These boxes
// cover the original *computed* interpolation, including its rounded endpoint.
extension RopeTriangleCollider {
    static func fpPairBox(_ a:SIMD3<Double>,_ b:SIMD3<Double>)->(SIMD3<Double>,SIMD3<Double>)? {
        let computed=a+(b-a)
        guard (0..<3).allSatisfy({a[$0].isFinite && computed[$0].isFinite}) else{return nil}
        return (simd_min(a,computed),simd_max(a,computed))
    }
    static func fpEdgeSquaredBound(low:SIMD3<Double>,high:SIMD3<Double>,a:SIMD3<Double>,b:SIMD3<Double>)->Double? {
        guard let edge=fpPairBox(a,b) else{return nil}
        let separation=simd_max(simd_max(edge.0-high,low-edge.1),SIMD3<Double>(repeating:0))
        let squared=simd_length_squared(separation)
        return squared.isFinite ? squared:nil
    }
}
