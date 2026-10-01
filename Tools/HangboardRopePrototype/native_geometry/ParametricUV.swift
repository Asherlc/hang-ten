import Foundation
import simd

struct RopeUVTile {
    let id: Int
    let a: SIMD2<Double>,b: SIMD2<Double>,c: SIMD2<Double>
}
struct RopeUVHit {let tile: Int,point: SIMD2<Double>}
private struct RopeUVNode {
    let low: SIMD2<Double>,high: SIMD2<Double>
    let left: Int,right: Int,tiles: [Int]
}
enum RopeUVError: Error {case invalidDomain}
enum RopeUVJSON {
    static func decode<T: Decodable>(_ type: T.Type,data: Data) throws -> T {
        try JSONDecoder().decode(type,from:data)
    }
}
enum RopeUVBroadPhase {
    static func mayTouch(start: SIMD3<Double>,end: SIMD3<Double>,low: SIMD3<Double>,high: SIMD3<Double>,threshold: Double) -> Bool {
        guard [start,end,low,high].allSatisfy({p in (0..<3).allSatisfy {p[$0].isFinite && abs(p[$0]) <= 10}}),
              (0..<3).allSatisfy({low[$0] <= high[$0]}),threshold.isFinite,(1e-6...1).contains(threshold) else {return true}
        let a = simd_min(start,end),b = simd_max(start,end)
        let gap = simd_max(simd_max(low-b,a-high),SIMD3(repeating:0))
        // Whole-link box separation, not midpoint separation. Differences
        // <=20m and squared sum <=1200m² give <1.066e-12m² rounding error.
        // 2e-12 also covers the subtraction used to lower the result.
        return !(simd_length_squared(gap)-2e-12 > (threshold*threshold).nextUp)
    }
}
struct RopeUVIndex {
    private let tiles: [RopeUVTile],nodes: [RopeUVNode]
    init(_ tiles: [RopeUVTile]) throws {
        guard tiles.allSatisfy({tile in [tile.a,tile.b,tile.c].allSatisfy {p in
            p.x.isFinite && p.y.isFinite && abs(p.x) <= 10 && abs(p.y) <= 10
        }}) else {throw RopeUVError.invalidDomain}
        self.tiles = tiles
        var nodes: [RopeUVNode] = []
        func build(_ ids: [Int]) -> Int {
            var low = SIMD2<Double>(repeating:.infinity),high = SIMD2<Double>(repeating:-.infinity)
            for i in ids {for p in [tiles[i].a,tiles[i].b,tiles[i].c] {low = simd_min(low,p);high = simd_max(high,p)}}
            let index = nodes.count
            nodes.append(RopeUVNode(low:low,high:high,left:-1,right:-1,tiles:ids))
            if ids.count > 8 {
                let axis = high.x-low.x >= high.y-low.y ? 0:1
                let sorted = ids.sorted {i,j in
                    let a = tiles[i].a[axis]+tiles[i].b[axis]+tiles[i].c[axis]
                    let b = tiles[j].a[axis]+tiles[j].b[axis]+tiles[j].c[axis]
                    return a == b ? i < j:a < b
                }
                let middle = sorted.count/2,left = build(Array(sorted[..<middle])),right = build(Array(sorted[middle...]))
                nodes[index] = RopeUVNode(low:low,high:high,left:left,right:right,tiles:[])
            }
            return index
        }
        if !tiles.isEmpty {_ = build(Array(tiles.indices))}
        self.nodes = nodes
    }
    func lookup(_ p: SIMD2<Double>,periodicU: Bool = false,periodicV: Bool = false) -> RopeUVHit? {
        guard !nodes.isEmpty,p.x.isFinite,p.y.isFinite,abs(p.x) <= 10,abs(p.y) <= 10 else {return nil}
        func orient(_ a: SIMD2<Double>,_ b: SIMD2<Double>,_ c: SIMD2<Double>) -> Double {
            let u = b-a,v = c-a
            return u.x*v.y-u.y*v.x
        }
        // Exact input coordinates are <=10. Each difference <=20, each
        // determinant's product sum <=800. Seven binary64 operations give
        // gamma_7*800 <6.22e-13 absolute error. 1e-10 also dominates subnormal
        // underflow. Strict signs retain edges/ambiguous predicates as fallback.
        let padding = 1e-10
        for du in periodicU ? [0,-2*Double.pi,2*Double.pi]:[0] {
            for dv in periodicV ? [0,-2*Double.pi,2*Double.pi]:[0] {
                // These are arbitrary chosen binary64 chart coordinates; the
                // returned point must be evaluated/measured by a distance
                // caller. We never claim floating 2*pi is an exact period.
                let q = p+SIMD2(du,dv)
                guard abs(q.x) <= 10,abs(q.y) <= 10 else {continue}
                var stack = [0]
                while let id = stack.popLast() {
                    let node = nodes[id]
                    if q.x < node.low.x || q.y < node.low.y || q.x > node.high.x || q.y > node.high.y {continue}
                    if node.left >= 0 {stack.append(node.left);stack.append(node.right);continue}
                    for id in node.tiles {
                        let t = tiles[id]
                        let d = orient(t.a,t.b,t.c),a = orient(q,t.b,t.c),b = orient(q,t.c,t.a),c = orient(q,t.a,t.b)
                        if (d > padding && a > padding && b > padding && c > padding) ||
                           (d < -padding && a < -padding && b < -padding && c < -padding) {
                            return RopeUVHit(tile:t.id,point:q)
                        }
                    }
                }
            }
        }
        return nil
    }
}
