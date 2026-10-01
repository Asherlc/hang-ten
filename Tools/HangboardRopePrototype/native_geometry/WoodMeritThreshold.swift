// Same-file diagnostic extension of the original collider. The app never
// selects it. Move only the existing root rejection ahead of ray parity.
extension RopeTriangleCollider {
    func screenRootSeparated(from a: SIMD3<Double>,to b: SIMD3<Double>,radius: Double) throws -> Bool {
        func bounded(_ p: SIMD3<Double>) -> Bool {(0..<3).allSatisfy{p[$0].isFinite && abs(p[$0])<=10}}
        let node=tree[0]
        guard bounded(a),bounded(b),bounded(node.minimum),bounded(node.maximum),
              radius.isFinite,(1e-6...1).contains(radius) else {
            throw RopePhysicsError.invalid("Invalid experimental root-separation domain")
        }
        let low=simd_min(a,b),high=simd_max(a,b)
        let gap=simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0))
        // Existing region-box derivation: at most20m component differences
        // and1200m² squared sums have <1.066e-12m² total error. Subtract
        // 2e-12 and compare an upper-rounded radius square. A true whole-link
        // separation also puts both endpoints outside the complete root box.
        // This is the existing root prune before parity, not a new broadphase.
        return simd_length_squared(gap)-2e-12 >= (radius*radius).nextUp
    }
    func screenRootParityOutside(from a: SIMD3<Double>,to b: SIMD3<Double>) -> Bool {
        !contains(a) && !contains(b)
    }
    func screenRootBounds() -> (SIMD3<Double>,SIMD3<Double>) {(tree[0].minimum,tree[0].maximum)}
    func screenExactWoodContacts(from a: SIMD3<Double>,to b: SIMD3<Double>,radius: Double) throws -> [RopeSegmentContact] {
        try screenRootSeparated(from:a,to:b,radius:radius) ? []:segmentContacts(from:a,to:b,radius:radius)
    }
}
