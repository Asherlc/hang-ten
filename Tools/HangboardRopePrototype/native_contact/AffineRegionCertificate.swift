import Foundation

/// Experimental certificate for immutable affine source rows, never a physical
/// coarse mesh. No nonlinear clearance assumption certifies an affine row.
final class AffineRegionCertificate {
    private struct Node {
        let first: Int, end: Int, group: Int, bounds: Int
        let minimum: Double, maximum: Double
        var left = -1, right = -1
    }
    private let packed: PackedFrozenRows
    private let nodes: [Node], roots: [Int], permutation: [Int]
    private let lower: [Double], upper: [Double]
    private(set) var lastExactRows = 0
    private(set) var lastCertifiedRows = 0
    private(set) var lastVisitedNodes = 0
    var nodeCount: Int { nodes.count }

    init(packed: PackedFrozenRows) throws {
        self.packed = packed
        var byGroup: [Int: [Int]] = [:]
        for id in packed.groups.indices { byGroup[packed.groups[id], default: []].append(id) }
        var nodes: [Node] = [], roots: [Int] = [], permutation: [Int] = []
        var lower: [Double] = [], upper: [Double] = []
        func coefficient(_ id: Int, _ axis: Int) -> Double {
            let count = packed.offsets[id+1] - packed.offsets[id]
            return axis < count ? packed.coefficients[packed.offsets[id]+axis] : packed.borders[id*packed.borderCount+axis-count]
        }
        func build(_ first: Int, _ end: Int, _ group: Int) throws -> Int {
            let id = permutation[first], count = packed.offsets[id+1] - packed.offsets[id] + packed.borderCount
            guard nodes.count < 8_000_000, count <= 8_000_000-lower.count else {
                throw RopePhysicsError.invalid("Affine region storage budget")
            }
            var lo = Array(repeating: Double.infinity, count: count)
            var hi = Array(repeating: -Double.infinity, count: count)
            var minimum = Double.infinity, maximum = -Double.infinity
            for offset in first..<end {
                let row = permutation[offset]
                minimum = min(minimum, packed.residuals[row]); maximum = max(maximum, packed.residuals[row])
                for axis in 0..<count {
                    let value = coefficient(row, axis)
                    lo[axis] = min(lo[axis], value); hi[axis] = max(hi[axis], value)
                }
            }
            let index = nodes.count, bounds = lower.count
            lower += lo; upper += hi
            nodes.append(Node(first: first, end: end, group: group, bounds: bounds, minimum: minimum, maximum: maximum))
            var splitAxis = count, width = maximum-minimum
            for axis in 0..<count where hi[axis]-lo[axis] > width {
                splitAxis = axis; width = hi[axis]-lo[axis]
            }
            // Identical rows remain a single region even above the working-QP
            // budget. The source is immutable and its whole range is certified.
            if end-first > 16 && width > 0 {
                let sorted = permutation[first..<end].sorted { a,b in
                    let av = splitAxis == count ? packed.residuals[a] : coefficient(a, splitAxis)
                    let bv = splitAxis == count ? packed.residuals[b] : coefficient(b, splitAxis)
                    return av == bv ? a < b : av < bv
                }
                permutation.replaceSubrange(first..<end, with: sorted)
                let middle = first+(end-first)/2
                let left = try build(first, middle, group), right = try build(middle, end, group)
                nodes[index].left = left; nodes[index].right = right
            }
            return index
        }
        for group in byGroup.keys.sorted() {
            let first = permutation.count
            permutation += byGroup[group]!
            roots.append(try build(first, permutation.count, group))
        }
        self.nodes = nodes; self.roots = roots; self.permutation = permutation
        self.lower = lower; self.upper = upper
    }

    func discover(_ vector: [Double], _ height: [Double], _ multipliers: [Double], _ included: Set<Int>) throws -> [Int] {
        guard vector.count == packed.size, height.count == packed.borderCount,
              multipliers.count == packed.residuals.count,
              vector.allSatisfy({ $0.isFinite }), height.allSatisfy({ $0.isFinite }),
              multipliers.allSatisfy({ $0.isFinite && $0 <= 1e-12 }),
              included.allSatisfy({ packed.residuals.indices.contains($0) }) else {
            throw RopePhysicsError.invalid("Invalid affine region query")
        }
        // Bound the exact original C - epsilon*mu initialization. Small positive
        // roundoff multipliers accepted by the working solver remain covered.
        let positive = (1e-8 * max(0, multipliers.max() ?? 0)).nextUp
        let negative = (1e-8 * min(0, multipliers.min() ?? 0)).nextDown
        var worst: [Int: (id: Int, gap: Double)] = [:], stack = roots
        lastExactRows = 0; lastCertifiedRows = 0; lastVisitedNodes = 0
        while let index = stack.popLast() {
            let node = nodes[index], firstID = permutation[node.first]
            let offset = packed.offsets[firstID], count = packed.offsets[firstID+1]-offset
            var lo = (node.minimum-positive).nextDown, hi = (node.maximum-negative).nextUp
            var finite = lo.isFinite && hi.isFinite
            // Every multiplication and sum is rounded outward in the original
            // sparse-term order, including duplicate support indices. Lower
            // bounds on nonlinear distances are never substituted here.
            for axis in 0..<(count+height.count) {
                let value = axis < count ? vector[packed.indices[offset+axis]] : height[axis-count]
                let a = lower[node.bounds+axis], b = upper[node.bounds+axis]
                let lowTerm = ((value >= 0 ? a : b)*value).nextDown
                let highTerm = ((value >= 0 ? b : a)*value).nextUp
                lo = (lo+lowTerm).nextDown; hi = (hi+highTerm).nextUp
                finite = finite && lo.isFinite && hi.isFinite
            }
            lastVisitedNodes += 1
            // The upper interval also proves all original intermediate values
            // finite. An overflow/uncertain interval falls back to exact rows.
            if finite && lo >= -1e-10 {
                lastCertifiedRows += node.end-node.first
                continue
            }
            if node.left >= 0 {
                stack.append(node.right); stack.append(node.left)
                continue
            }
            for offset in node.first..<node.end {
                let id = permutation[offset]
                var gap = packed.residuals[id]-1e-8*multipliers[id]
                for k in packed.offsets[id]..<packed.offsets[id+1] {
                    gap += packed.coefficients[k]*vector[packed.indices[k]]
                }
                for k in height.indices { gap += packed.borders[id*height.count+k]*height[k] }
                lastExactRows += 1
                guard gap.isFinite else { throw RopePhysicsError.invalid("Nonfinite affine region fallback") }
                if gap < -1e-10 {
                    guard !included.contains(id) else { throw RopePhysicsError.invalid("Admitted region row fails certificate") }
                    let previous = worst[node.group]
                    if previous == nil || gap < previous!.gap || (gap == previous!.gap && id < previous!.id) {
                        worst[node.group] = (id, gap)
                    }
                }
            }
        }
        return worst.values.map { $0.id }.sorted()
    }
}
