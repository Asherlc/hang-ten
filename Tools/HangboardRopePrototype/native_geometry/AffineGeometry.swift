// Experimental original-geometry to frozen-affine bridge. Appended to the
// unchanged collider source by the owned tool, never selected by the app.
extension RopeTriangleCollider {
    func screenAffinelyClear(from start: SIMD3<Double>, to end: SIMD3<Double>,
                             requiredClearance: Double,
                             startCorrection: SIMD3<Double>, endCorrection: SIMD3<Double>,
                             thresholdRegions: Bool = false) throws -> Bool {
        func bounded(_ p: SIMD3<Double>) -> Bool {
            (0..<3).allSatisfy { p[$0].isFinite && abs(p[$0]) <= 10 }
        }
        guard bounded(start), bounded(end), bounded(startCorrection), bounded(endCorrection),
              bounded(tree[0].minimum), bounded(tree[0].maximum),
              requiredClearance.isFinite, (1e-6...1).contains(requiredClearance) else {
            throw RopePhysicsError.invalid("Invalid original-affine geometry proof domain")
        }
        // For every original triangle witness, d >= d_min and |n| = 1.
        // Every material-fraction correction is a convex endpoint combination:
        // C + J*delta >= d_min - requiredClearance - max(|delta_a|,|delta_b|).
        // Deltas are board-relative, so coupled height translation is included
        // exactly by the caller. This bounds original affine rows, not merely
        // nonlinear clearance at the displaced segment. Omitted multipliers
        // must be zero; this cannot replace an admitted-row KKT certificate.
        let movement = max(simd_length(startCorrection),simd_length(endCorrection))
        // Original triangle arithmetic remains the authority. Bound its tiny
        // unit-normal roundoff and retain an additional 1 nm uncertainty band
        // inside this bounded metre-scale domain; uncertain queries fall back.
        let threshold = (requiredClearance+(movement*(1+1e-12)).nextUp).nextUp+1e-9
        if thresholdRegions {
            // Threshold traversal avoids finding an exact nearest surface or
            // producing normals/manifolds. Every uncertain leaf keeps original
            // triangle tests; original sign and whole-segment crossings remain.
            guard !contains(start), start == end || !contains(end) else {return false}
            let low = simd_min(start,end),high = simd_max(start,end)
            let squared = (threshold*threshold).nextUp
            func clear(_ minimum: SIMD3<Double>,_ maximum: SIMD3<Double>) -> Bool {
                var bound = 0.0
                for axis in 0..<3 {
                    let gap = max(0,max((minimum[axis]-high[axis]).nextDown,(low[axis]-maximum[axis]).nextDown))
                    bound = (bound+(gap*gap).nextDown).nextDown
                }
                return bound > squared
            }
            func close(_ p: SIMD3<Double>,_ q: SIMD3<Double>) -> Bool {
                simd_length_squared(p-q) <= squared
            }
            var stack = [0]
            while let index = stack.popLast() {
                let node = tree[index]
                if clear(node.minimum,node.maximum) {continue}
                if node.left >= 0 {stack.append(node.left);stack.append(node.right);continue}
                for id in node.faces {
                    let face = mesh.triangles[id],a = mesh.vertices[face.x],b = mesh.vertices[face.y],c = mesh.vertices[face.z]
                    if clear(simd_min(a,simd_min(b,c)),simd_max(a,simd_max(b,c))) {continue}
                    if close(start,Self.triangleClosest(start,a,b,c)) {return false}
                    if start != end {
                        if close(end,Self.triangleClosest(end,a,b,c)) {return false}
                        if let t = Self.rayTriangle(start,end-start,a,b,c),t >= 0,t <= 1 {return false}
                        for (u,v) in [(a,b),(b,c),(c,a)] {
                            let pair = Self.segmentPair(start,end,u,v)
                            if close(pair.0,pair.1) {return false}
                        }
                    }
                }
            }
            return true
        }
        let distance = start == end ? signedDistance(at:start):segmentClearance(from:start,to:end)
        return distance.isFinite && distance.nextDown > threshold
    }
}
