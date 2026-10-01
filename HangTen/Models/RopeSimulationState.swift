import simd

struct RopePortalCrossing: Sendable, Equatable {
    let segment: Int
    let fraction: Double
    var materialCoordinate: Double { Double(segment)+fraction }
    func point(in positions: [SIMD3<Double>]) -> SIMD3<Double> {
        positions[segment]+(positions[segment+1]-positions[segment])*fraction
    }
}

struct RopeChannelSpan: Sendable {
    let start: RopePortalCrossing
    let end: RopePortalCrossing
}

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
    // Seed labels only. Runtime topology follows geometric crossings and
    // never constrains these particular material particles to a mouth.
    let portals: [Int: String]
    let channelSegments: [Int: String]
    var portalCrossings: [String: RopePortalCrossing] = [:]
    var channelSpans: [String: RopeChannelSpan] = [:]
}

struct RopeSimulationState: Sendable {
    let profileID: String
    let boardMass: Double
    var boardHeight: Double
    var boardVerticalVelocity: Double
    var orientation: simd_quatd
    var ropes: [RopeChainState]
    /// Board-local center of its evidenced cord attachments/passages.
    /// Height remains a gravity-driven degree of freedom at this pivot.
    var rotationPivot: SIMD3<Double> = .zero

    func boardPoint(_ world: SIMD3<Double>) -> SIMD3<Double> {
        rotationPivot + orientation.inverse.act(world - rotationPivot - SIMD3(0,boardHeight,0))
    }
    func worldPoint(_ board: SIMD3<Double>) -> SIMD3<Double> {
        orientation.act(board - rotationPivot) + rotationPivot + SIMD3(0,boardHeight,0)
    }
}

struct RopePortalBoundaryConstraint: Sendable {
    let residual: Double
    let firstGradient: SIMD3<Double>
    let secondGradient: SIMD3<Double>
}

enum RopePassageTopology {
    /// Finds the ordered crossings of the evidenced graph. A crossing can
    /// move through consecutive links while material rest lengths stay fixed.
    static func refresh(state: inout RopeSimulationState, input: RopePhysicsInput) throws {
        guard let profile=input.profiles.first(where:{$0.id == state.profileID}) else {
            throw RopePhysicsError.invalid("Missing topology profile")
        }
        let portals=Dictionary(uniqueKeysWithValues:input.portals.map{($0.id,$0)})
        for r in state.ropes.indices {
            guard let graph=profile.ropes.first(where:{$0.id == state.ropes[r].id}) else {
                throw RopePhysicsError.invalid("Missing topology graph")
            }
            let points=state.ropes[r].positions.map{state.boardPoint($0)}
            var crossings:[String:RopePortalCrossing]=[:]
            var previous = -Double.infinity
            for node in graph.nodes {
                guard let id=node.portalID,let portal=portals[id] else {continue}
                var candidates:[RopePortalCrossing]=[]
                for i in 0..<(points.count-1) {
                    let a=points[i],delta=points[i+1]-a
                    let denominator=simd_dot(delta,portal.normal)
                    guard abs(denominator)>1e-12 else {continue}
                    let f=simd_dot(portal.center-a,portal.normal)/denominator
                    guard f >= -1e-8,f <= 1+1e-8 else {continue}
                    let crossing=RopePortalCrossing(segment:i,fraction:min(1,max(0,f)))
                    guard crossing.materialCoordinate>previous+1e-7 else {continue}
                    let point=a+delta*crossing.fraction
                    // Leave a bounded recovery region for an inertial trial;
                    // acceptance separately checks the eroded actual aperture.
                    guard boundaryMargin(point,portal:portal) >= -0.002 else {continue}
                    candidates.append(crossing)
                }
                guard let selected=candidates.min(by:{$0.materialCoordinate<$1.materialCoordinate}) else {
                    throw RopePhysicsError.invalid("Lost ordered portal crossing \(id)")
                }
                crossings[id]=selected;previous=selected.materialCoordinate
            }
            var spans:[String:RopeChannelSpan]=[:]
            for (i,edge) in graph.edges.enumerated() where edge.kind == "channel" {
                guard let id=edge.channelID,let a=graph.nodes[i].portalID,let b=graph.nodes[i+1].portalID,
                      let start=crossings[a],let end=crossings[b],start.materialCoordinate<end.materialCoordinate else {
                    throw RopePhysicsError.invalid("Lost channel traversal")
                }
                spans[id]=RopeChannelSpan(start:start,end:end)
            }
            state.ropes[r].portalCrossings=crossings
            state.ropes[r].channelSpans=spans
        }
    }

    /// Derivatives of an eroded aperture half-space at the geometric plane
    /// intersection. Its fraction changes with the endpoints, so material can
    /// feed through the passage without pinning either endpoint to the mouth.
    static func boundaryConstraints(from a:SIMD3<Double>,to b:SIMD3<Double>,
                                    portal:RopePortalRegion,radius:Double) throws -> [RopePortalBoundaryConstraint] {
        let delta=b-a,denominator=simd_dot(delta,portal.normal)
        guard abs(denominator)>1e-12 else {throw RopePhysicsError.invalid("Tangent portal crossing")}
        let fraction=simd_dot(portal.center-a,portal.normal)/denominator
        guard fraction>=(-1e-8),fraction<=1+1e-8 else {throw RopePhysicsError.invalid("Missing portal crossing")}
        let f=min(1,max(0,fraction)),point=a+f*delta
        return portal.boundary.indices.map {i in
            let start=portal.boundary[i],end=portal.boundary[(i+1)%portal.boundary.count]
            var inward=simd_normalize(simd_cross(portal.normal,end-start))
            if simd_dot(inward,portal.center-start)<0 {inward = -inward}
            let gradient=inward-portal.normal*(simd_dot(inward,delta)/denominator)
            return RopePortalBoundaryConstraint(residual:simd_dot(point-start,inward)-radius-RopeRegionGeometry.clearance,
                firstGradient:gradient*(1-f),secondGradient:gradient*f)
        }
    }

    static func boundaryMargin(_ point: SIMD3<Double>,portal: RopePortalRegion) -> Double {
        portal.boundary.indices.reduce(Double.infinity) {value,i in
            let a=portal.boundary[i],b=portal.boundary[(i+1)%portal.boundary.count]
            var inward=simd_normalize(simd_cross(portal.normal,b-a))
            if simd_dot(inward,portal.center-a)<0 {inward = -inward}
            return min(value,simd_dot(point-a,inward))
        }
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
