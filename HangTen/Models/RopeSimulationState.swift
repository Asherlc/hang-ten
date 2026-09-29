import simd

struct RopeChainState: Sendable {
    let id: String
    let radius: Double
    let linearMass: Double
    let restLengths: [Double]
    var positions: [SIMD3<Double>]
    var previousPositions: [SIMD3<Double>]
    var velocities: [SIMD3<Double>]
    let supports: [Int: SIMD3<Double>]
    let attachments: [Int: SIMD3<Double>]
    let portals: [Int: String]
    let channelSegments: [Int: String]
}

struct RopeSimulationState: Sendable {
    let profileID: String
    let boardMass: Double
    var boardHeight: Double
    var boardVerticalVelocity: Double
    var orientation: simd_quatd
    var ropes: [RopeChainState]

    func boardPoint(_ world: SIMD3<Double>) -> SIMD3<Double> {
        orientation.inverse.act(world - SIMD3(0,boardHeight,0))
    }
    func worldPoint(_ board: SIMD3<Double>) -> SIMD3<Double> {
        orientation.act(board) + SIMD3(0,boardHeight,0)
    }
}

enum RopeRegionGeometry {
    static let clearance = 0.0001

    /// Convex planar polygon erosion; keeps every centerline one real radius
    /// plus the declared clearance from the native aperture's boundary.
    static func erodedBoundary(_ portal: RopePortalRegion, radius: Double) throws -> [SIMD3<Double>] {
        guard radius.isFinite, radius > 0 else { throw RopePhysicsError.invalid("Invalid rope radius") }
        var polygon = portal.boundary
        for i in portal.boundary.indices {
            let a=portal.boundary[i], b=portal.boundary[(i+1)%portal.boundary.count]
            var inward=simd_normalize(simd_cross(portal.normal,b-a))
            if simd_dot(inward,portal.center-a) < 0 { inward = -inward }
            let offset=radius+clearance
            let old=polygon; polygon=[]
            guard !old.isEmpty else { break }
            for j in old.indices {
                let p=old[j], q=old[(j+1)%old.count]
                let dp=simd_dot(p-a,inward)-offset, dq=simd_dot(q-a,inward)-offset
                if dp >= -1e-12 { polygon.append(p) }
                if (dp >= 0) != (dq >= 0) { polygon.append(p+(q-p)*(dp/(dp-dq))) }
            }
        }
        guard polygon.count >= 3 else { throw RopePhysicsError.invalid("Thick rope does not fit eroded portal \(portal.id)") }
        return polygon
    }

    static func bearing(_ portal: RopePortalRegion, radius: Double, up: SIMD3<Double>) throws -> SIMD3<Double> {
        let polygon=try erodedBoundary(portal,radius:radius)
        let scores=polygon.map { simd_dot($0,up) }, maximum=scores.max()!
        let ties=polygon.indices.filter { maximum-scores[$0] < 1e-10 }
        return ties.reduce(SIMD3<Double>.zero) { $0+polygon[$1] }/Double(ties.count)
    }
}
