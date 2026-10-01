// Experimental original-geometry to frozen-affine bridge. Appended to the
// unchanged collider source by the owned tool, never selected by the app.
extension RopeTriangleCollider {
    func screenAffinelyClear(from start: SIMD3<Double>, to end: SIMD3<Double>,
                             requiredClearance: Double,
                             startCorrection: SIMD3<Double>, endCorrection: SIMD3<Double>,
                             thresholdRegions: Bool = false, fastRegionBoxes: Bool = false) throws -> Bool {
        try screenAffinelyClear(from:start,to:end,requiredClearance:requiredClearance,
            startCorrection:startCorrection,endCorrection:endCorrection,
            thresholdRegions:thresholdRegions,fastRegionBoxes:fastRegionBoxes,slabs:nil)
    }
    fileprivate func screenAffinelyClear(from start: SIMD3<Double>, to end: SIMD3<Double>,
                             requiredClearance: Double,
                             startCorrection: SIMD3<Double>, endCorrection: SIMD3<Double>,
                             thresholdRegions: Bool, fastRegionBoxes: Bool,
                             slabs: RopeAffineSlabIndex?) throws -> Bool {
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
        // Original triangle arithmetic remains the authority. This pilot uses
        // a 1 nm uncertainty band and independently checks every omitted
        // original row on its fixed input. That padding is not a proved error
        // bound for the general triangle kernel; no runtime adoption follows.
        let threshold = (requiredClearance+(movement*(1+1e-12)).nextUp).nextUp+1e-9
        if thresholdRegions {
            // Threshold traversal avoids finding an exact nearest surface or
            // producing normals/manifolds. Every uncertain leaf keeps original
            // triangle tests; original sign and whole-segment crossings remain.
            guard !contains(start), start == end || !contains(end) else {return false}
            let low = simd_min(start,end),high = simd_max(start,end)
            let squared = (threshold*threshold).nextUp
            func clear(_ minimum: SIMD3<Double>,_ maximum: SIMD3<Double>) -> Bool {
                if fastRegionBoxes {
                    let gap = simd_max(simd_max(minimum-high,low-maximum),SIMD3(repeating:0))
                    // All coordinates are bounded by10m: differences <=20m,
                    // sum of squared gaps <=1200m². Subtraction/product/sum
                    // absolute error is below1e-12m² even without fused math.
                    // Subtract2e-12m², including rounding of this subtraction,
                    // to obtain a conservative lower bound in one SIMD path.
                    return simd_length_squared(gap)-2e-12 > squared
                }
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
                if clear(node.minimum,node.maximum) || (slabs?.nodes[index].lowerBound(from:start,to:end) ?? 0) > threshold {continue}
                if node.left >= 0 {stack.append(node.left);stack.append(node.right);continue}
                for id in node.faces {
                    let face = mesh.triangles[id],a = mesh.vertices[face.x],b = mesh.vertices[face.y],c = mesh.vertices[face.z]
                    if clear(simd_min(a,simd_min(b,c)),simd_max(a,simd_max(b,c))) || (slabs?.faces[id].lowerBound(from:start,to:end) ?? 0) > threshold {continue}
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

// Immutable experimental index retains the collider it bounds, preventing a
// certificate from being paired with a different mesh.
struct RopeAffineSlab {
    private let axis: SIMD3<Double>
    private let low: Double,high: Double,normUpper: Double
    init(vertices: [SIMD3<Double>], axis: SIMD3<Double>) {
        guard !vertices.isEmpty,vertices.allSatisfy({p in (0..<3).allSatisfy {p[$0].isFinite && abs(p[$0]) <= 10}}),
              (0..<3).allSatisfy({axis[$0].isFinite && abs(axis[$0]) <= 2}) else {
            self.axis = .zero;low = 0;high = 0;normUpper = 0;return
        }
        self.axis = axis
        var squared = 0.0
        for k in 0..<3 {squared = (squared+(axis[k]*axis[k]).nextUp).nextUp}
        normUpper = sqrt(squared).nextUp
        var minimum = Double.infinity,maximum = -Double.infinity
        for p in vertices {let d = simd_dot(axis,p);minimum = min(minimum,d);maximum = max(maximum,d)}
        // Exact direction components are <=2 and coordinates <=10m. A dot
        // has absolute sum <=60m and <=5 binary64 rounding operations:
        // gamma_5*60 <3.34e-14m. 1e-12m covers dot and bound expansion.
        low = (minimum-1e-12).nextDown;high = (maximum+1e-12).nextUp
    }
    func lowerBound(minimum: SIMD3<Double>,maximum: SIMD3<Double>) -> Double {
        var lo = minimum,hi = maximum
        for k in 0..<3 where axis[k] < 0 {lo[k] = maximum[k];hi[k] = minimum[k]}
        return lowerBound(from:lo,to:hi)
    }
    func lowerBound(from start: SIMD3<Double>,to end: SIMD3<Double>) -> Double {
        guard normUpper > 1e-100,
              (0..<3).allSatisfy({start[$0].isFinite && end[$0].isFinite && abs(start[$0]) <= 10 && abs(end[$0]) <= 10}) else {return 0}
        let a = simd_dot(axis,start),b = simd_dot(axis,end)
        let queryLow = (min(a,b)-1e-12).nextDown,queryHigh = (max(a,b)+1e-12).nextUp
        let gap = max(0,max((low-queryHigh).nextDown,(queryLow-high).nextDown))
        return max(0,(gap/normUpper).nextDown)
    }
}
struct RopeAffineSlabIndex {
    fileprivate let collider: RopeTriangleCollider
    fileprivate let nodes: [RopeAffineSlab]
    fileprivate let faces: [RopeAffineSlab]
    func screenBatch(_ queries: [RopeAffineQuery]) throws -> [Bool] {
        try collider.screenBatch(queries,slabs:self)
    }
    func screenAffinelyClear(from start: SIMD3<Double>,to end: SIMD3<Double>,
                            requiredClearance: Double,startCorrection: SIMD3<Double>,endCorrection: SIMD3<Double>) throws -> Bool {
        try collider.screenAffinelyClear(from:start,to:end,requiredClearance:requiredClearance,
            startCorrection:startCorrection,endCorrection:endCorrection,thresholdRegions:true,fastRegionBoxes:true,slabs:self)
    }
}
extension RopeTriangleCollider {
    func originalSignClassifications(at points: [SIMD3<Double>]) -> [Bool] {
        points.map {contains($0)}
    }
    func affineSlabIndex() -> RopeAffineSlabIndex {
        let normals = mesh.triangles.map {face in
            simd_cross(mesh.vertices[face.y]-mesh.vertices[face.x],mesh.vertices[face.z]-mesh.vertices[face.x])
        }
        func axis(_ faces: [Int]) -> SIMD3<Double> {
            let sum = faces.reduce(SIMD3<Double>.zero) {$0+normals[$1]}
            return simd_length_squared(sum) > 1e-100 ? simd_normalize(sum):.zero
        }
        let empty = RopeAffineSlab(vertices:[],axis:.zero)
        var nodeSlabs = [RopeAffineSlab](repeating:empty,count:tree.count)
        func build(_ id: Int) -> [Int] {
            let node = tree[id]
            let faces = node.left >= 0 ? build(node.left)+build(node.right):node.faces
            let points = faces.flatMap {i in (0..<3).map {mesh.vertices[mesh.triangles[i][$0]]}}
            nodeSlabs[id] = RopeAffineSlab(vertices:points,axis:axis(faces))
            return faces
        }
        _ = build(0)
        let faceSlabs = mesh.triangles.indices.map {i in
            RopeAffineSlab(vertices:(0..<3).map {mesh.vertices[mesh.triangles[i][$0]]},axis:simd_normalize(normals[i]))
        }
        return RopeAffineSlabIndex(collider:self,nodes:nodeSlabs,faces:faceSlabs)
    }
}

struct RopeAffineQuery {
    let start: SIMD3<Double>,end: SIMD3<Double>
    let requiredClearance: Double,startCorrection: SIMD3<Double>,endCorrection: SIMD3<Double>
}

private struct RopeAffinePacket {
    let low: SIMD3<Double>,high: SIMD3<Double>,threshold: Double
    let left: Int,right: Int,queries: [Int]
}
extension RopeTriangleCollider {
    fileprivate func screenBatch(_ queries: [RopeAffineQuery],slabs: RopeAffineSlabIndex) throws -> [Bool] {
        guard !queries.isEmpty else {return []}
        func bounded(_ p: SIMD3<Double>) -> Bool {(0..<3).allSatisfy {p[$0].isFinite && abs(p[$0]) <= 10}}
        guard bounded(tree[0].minimum),bounded(tree[0].maximum) else {
            throw RopePhysicsError.invalid("Invalid batch mesh proof domain")
        }
        let thresholds = try queries.map {q -> Double in
            guard bounded(q.start),bounded(q.end),bounded(q.startCorrection),bounded(q.endCorrection),
                  q.requiredClearance.isFinite,(1e-6...1).contains(q.requiredClearance) else {
                throw RopePhysicsError.invalid("Invalid batch query proof domain")
            }
            let movement = max(simd_length(q.startCorrection),simd_length(q.endCorrection))
            return (q.requiredClearance+(movement*(1+1e-12)).nextUp).nextUp+1e-9
        }
        var packets: [RopeAffinePacket] = []
        func build(_ ids: [Int]) -> Int {
            var low = SIMD3<Double>(repeating:.infinity),high = SIMD3<Double>(repeating:-.infinity),threshold = 0.0
            for i in ids {let q = queries[i];low = simd_min(low,simd_min(q.start,q.end));high = simd_max(high,simd_max(q.start,q.end));threshold = max(threshold,thresholds[i])}
            let index = packets.count
            packets.append(RopeAffinePacket(low:low,high:high,threshold:threshold,left:-1,right:-1,queries:ids))
            if ids.count > 4 {
                let size = high-low,axis = size.x >= size.y && size.x >= size.z ? 0:(size.y >= size.z ? 1:2)
                let sorted = ids.sorted {a,b in
                    let x = queries[a].start[axis]+queries[a].end[axis],y = queries[b].start[axis]+queries[b].end[axis]
                    return x == y ? a < b:x < y
                }
                let middle = sorted.count/2,left = build(Array(sorted[..<middle])),right = build(Array(sorted[middle...]))
                packets[index] = RopeAffinePacket(low:low,high:high,threshold:threshold,left:left,right:right,queries:[])
            }
            return index
        }
        _ = build(Array(queries.indices))
        var clear = [Bool](repeating:true,count:queries.count),stack = [(0,0)]
        while let (wood,rope) = stack.popLast() {
            let node = tree[wood],packet = packets[rope]
            let gap = simd_max(simd_max(node.minimum-packet.high,packet.low-node.maximum),SIMD3(repeating:0))
            if simd_length_squared(gap)-2e-12 > (packet.threshold*packet.threshold).nextUp ||
                slabs.nodes[wood].lowerBound(minimum:packet.low,maximum:packet.high) > packet.threshold {continue}
            if node.left < 0 && packet.left < 0 {
                for i in packet.queries where clear[i] {
                    let q = queries[i],threshold = thresholds[i],square = (threshold*threshold).nextUp
                    let low = simd_min(q.start,q.end),high = simd_max(q.start,q.end)
                    func close(_ p: SIMD3<Double>,_ r: SIMD3<Double>) -> Bool {simd_length_squared(p-r) <= square}
                    for faceID in node.faces {
                        let face = mesh.triangles[faceID],a = mesh.vertices[face.x],b = mesh.vertices[face.y],c = mesh.vertices[face.z]
                        let separation = simd_max(simd_max(simd_min(a,simd_min(b,c))-high,low-simd_max(a,simd_max(b,c))),SIMD3(repeating:0))
                        if simd_length_squared(separation)-2e-12 > square || slabs.faces[faceID].lowerBound(from:q.start,to:q.end) > threshold {continue}
                        if close(q.start,Self.triangleClosest(q.start,a,b,c)) {clear[i] = false;break}
                        if q.start != q.end {
                            if close(q.end,Self.triangleClosest(q.end,a,b,c)) {clear[i] = false;break}
                            if let t = Self.rayTriangle(q.start,q.end-q.start,a,b,c),t >= 0,t <= 1 {clear[i] = false;break}
                            for (u,v) in [(a,b),(b,c),(c,a)] {
                                let pair = Self.segmentPair(q.start,q.end,u,v)
                                if close(pair.0,pair.1) {clear[i] = false;break}
                            }
                            if !clear[i] {break}
                        }
                    }
                }
                continue
            }
            let woodSize = node.maximum-node.minimum,ropeSize = packet.high-packet.low
            let splitWood = node.left >= 0 && (packet.left < 0 || max(woodSize.x,max(woodSize.y,woodSize.z)) >= max(ropeSize.x,max(ropeSize.y,ropeSize.z)))
            if splitWood {stack.append((node.left,rope));stack.append((node.right,rope))}
            else {stack.append((wood,packet.left));stack.append((wood,packet.right))}
        }
        // Cache only identical finite points against this same immutable mesh
        // within this batch. Original ray/parity classification remains exact.
        var inside: [SIMD3<Double>:Bool] = [:];inside.reserveCapacity(queries.count)
        func isInside(_ p: SIMD3<Double>) -> Bool {
            if let value = inside[p] {return value}
            let value = contains(p);inside[p] = value;return value
        }
        for i in queries.indices where clear[i] {
            let q = queries[i]
            if isInside(q.start) || (q.start != q.end && isInside(q.end)) {clear[i] = false}
        }
        return clear
    }
}
