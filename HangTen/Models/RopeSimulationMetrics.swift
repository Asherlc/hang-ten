import simd

struct RopeChainSnapshot: Sendable {
    let id: String
    let radius: Double
    let positions: [SIMD3<Double>]
}

struct RopeFrameSnapshot: Sendable {
    let boardHeight: Double
    let orientation: simd_quatd
    let ropes: [RopeChainSnapshot]
    let settled: Bool
    let metrics: RopeSimulationMetrics
}

/// Immutable native-channel BVHs, bound to all authored region geometry.
/// Sharing this value across transactional solver copies does not rebuild or
/// mutate the collision structures. A different region set is rejected.
struct RopeChannelColliderCache: Sendable {
    private let channels:[RopeChannelRegion]
    private let colliders:[String:RopeTriangleCollider]

    init(channels:[RopeChannelRegion]) throws {
        guard Set(channels.map{$0.id}).count==channels.count else {
            throw RopePhysicsError.invalid("Duplicate channel collider ID")
        }
        self.channels=channels
        colliders=Dictionary(uniqueKeysWithValues:try channels.map{($0.id,try RopeTriangleCollider(mesh:$0.solid))})
    }

    func matchingColliders(for channels:[RopeChannelRegion]) throws -> [String:RopeTriangleCollider] {
        guard self.channels==channels else {throw RopePhysicsError.invalid("Channel collider cache geometry mismatch")}
        return colliders
    }
}

struct RopeSimulationMetrics: Sendable {
    let totalLengthError: Double
    let maximumLocalStrain: Double
    let minimumSegmentClearance: Double
    let minimumClearanceMargin: Double
    let topologyValid: Bool
    let topologyFailure: String?
    let maximumSpeed: Double
    let boardDisplacement: Double

    var geometryAccepted: Bool {
        totalLengthError <= 0.0005 && maximumLocalStrain <= 0.005 && minimumClearanceMargin >= -0.00005 && topologyValid
    }

    static func selfContactValid(positions:[SIMD3<Double>],radius:Double,
                                 supports:[Int:SIMD3<Double>]) -> Bool {
        selfContactPair(positions:positions,radius:radius,supports:supports) == nil
    }

    static func selfContactPair(positions:[SIMD3<Double>],radius:Double,
                               supports:[Int:SIMD3<Double>],margin:Double=0,restLengths:[Double]?=nil) -> SIMD2<Int>? {
        contacts(positions:positions,radius:radius,supports:supports,margin:margin,
                 restLengths:restLengths,stopAfterFirst:true).first
    }

    /// Enumerate the complete manifold so constraint selection and nonlinear
    /// merit do not jump between overlapping pairs as the first pair separates.
    static func selfContactPairs(positions:[SIMD3<Double>],radius:Double,
                                supports:[Int:SIMD3<Double>],margin:Double=0,restLengths:[Double]?=nil) -> [SIMD2<Int>] {
        contacts(positions:positions,radius:radius,supports:supports,margin:margin,
                 restLengths:restLengths,stopAfterFirst:false)
    }

    private static func contacts(positions:[SIMD3<Double>],radius:Double,
                               supports:[Int:SIMD3<Double>],margin:Double=0,restLengths:[Double]?,stopAfterFirst:Bool) -> [SIMD2<Int>] {
        var pairs:[SIMD2<Int>]=[]
        let links=positions.count-1
        guard links>0 else{return [SIMD2(0,0)]}
        var arc=[0.0]
        for i in 0..<links {arc.append(arc.last!+(restLengths?[i] ?? simd_distance(positions[i],positions[i+1])))}
        let commonSupport = supports[0].flatMap { start in
            supports[links].flatMap { end in simd_distance(start,end)<1e-10 ? start:nil }
        }
        for i in 0..<links {
            for j in (i+1)..<links {
                // Connected capsules overlap around bends. This exclusion is
                // based on intrinsic arc distance, never array index alone.
                if j == i+1 {continue}
                let connectedNeighborhood = arc[j]-arc[i+1] < Double.pi*radius
                let commonNeighborhood:Bool
                if commonSupport != nil {
                    let total=arc.last!
                    commonNeighborhood = min(arc[i],total-arc[i+1])<4*radius && min(arc[j],total-arc[j+1])<4*radius
                } else {commonNeighborhood=false}
                let low=simd_min(positions[i],positions[i+1]),high=simd_max(positions[i],positions[i+1])
                let otherLow=simd_min(positions[j],positions[j+1]),otherHigh=simd_max(positions[j],positions[j+1])
                let separation=simd_max(simd_max(low-otherHigh,otherLow-high),SIMD3(repeating:0))
                if simd_length_squared(separation) >= pow(2*radius-0.00005+margin,2) {continue}
                let pair=RopeTriangleCollider.segmentPair(positions[i],positions[i+1],positions[j],positions[j+1])
                let distance=simd_distance(pair.0,pair.1)
                // Capsules within one bend share volume along the continuous
                // tube. A proper centerline crossing remains invalid there.
                if commonNeighborhood {
                    if distance<1e-8,let commonSupport,simd_distance(pair.0,commonSupport)>1e-6 {pairs.append(SIMD2(i,j));if stopAfterFirst{return pairs}}
                } else if connectedNeighborhood {
                    if distance<1e-8 && pair.2>1e-6 && pair.2<1-1e-6 {pairs.append(SIMD2(i,j));if stopAfterFirst{return pairs}}
                } else if distance < 2*radius-0.00005+margin {pairs.append(SIMD2(i,j));if stopAfterFirst{return pairs}}
            }
        }
        return pairs
    }

    static func measure(state:RopeSimulationState,input:RopePhysicsInput,collider:RopeTriangleCollider,
                        boardHistory:[Double],includeSelfContact:Bool=true,channelCache:RopeChannelColliderCache?=nil) throws -> Self {
        var totalError=0.0,strain=0.0,clearance=Double.infinity,topology=true,speed=abs(state.boardVerticalVelocity)
        var failure:String?
        var margin=Double.infinity
        let portals=Dictionary(uniqueKeysWithValues:input.portals.map{($0.id,$0)})
        let channels=Dictionary(uniqueKeysWithValues:input.channels.map{($0.id,$0)})
        let channelColliders=try (channelCache ?? RopeChannelColliderCache(channels:input.channels)).matchingColliders(for:input.channels)
        for rope in state.ropes {
            var length=0.0
            for i in rope.restLengths.indices {
                let distance=simd_distance(rope.positions[i],rope.positions[i+1])
                length += distance;strain=max(strain,abs(distance/rope.restLengths[i]-1))
                let a=state.boardPoint(rope.positions[i]),b=state.boardPoint(rope.positions[i+1])
                let segmentClearance=collider.segmentClearance(from:a,to:b)
                clearance=min(clearance,segmentClearance);margin=min(margin,segmentClearance-rope.radius)
                for (id,span) in rope.channelSpans {
                    let lo=max(Double(i),span.start.materialCoordinate),hi=min(Double(i+1),span.end.materialCoordinate)
                    guard hi>lo+1e-9 else {continue}
                    guard let region=channels[id] else{throw RopePhysicsError.invalid("Missing channel membership")}
                    for fraction in [lo-Double(i),(lo+hi)/2-Double(i),hi-Double(i)] {
                        let point=a+(b-a)*fraction
                        if channelColliders[region.id]!.signedDistance(at:point)>1e-5 {
                            topology=false;failure="Outside channel at link \(i)"
                        }
                    }
                }
            }
            totalError=max(totalError,abs(length-rope.restLengths.reduce(0,+)))
            for (index,point) in rope.supports where simd_distance(point,rope.positions[index])>1e-8 {topology=false;failure="Support \(index) moved"}
            for (id,crossing) in rope.portalCrossings {
                guard let portal=portals[id] else{throw RopePhysicsError.invalid("Missing portal membership")}
                let p=state.boardPoint(crossing.point(in:rope.positions))
                if abs(simd_dot(p-portal.center,portal.normal))>1e-5 {topology=false;failure="Portal \(id) left plane"}
                if RopePassageTopology.boundaryMargin(p,portal:portal)<rope.radius+RopeRegionGeometry.clearance-0.00006 {
                    topology=false;failure="Portal \(id) left eroded aperture"
                }
            }
            if includeSelfContact,let pair=selfContactPair(positions:rope.positions,radius:rope.radius,supports:rope.supports,restLengths:rope.restLengths) {topology=false;failure="Self contact \(pair) at \(rope.positions[pair.x]), \(rope.positions[pair.y])"}
            for velocity in rope.velocities {speed=max(speed,simd_length(velocity))}
        }
        if includeSelfContact {
            for first in state.ropes.indices {
                for second in state.ropes.indices where second>first {
                    if !RopeCordContacts.between(state.ropes[first],state.ropes[second]).isEmpty {
                        topology=false;failure="Contact between ropes \(state.ropes[first].id) and \(state.ropes[second].id)"
                    }
                }
            }
        }
        let displacement=(boardHistory.max() ?? state.boardHeight)-(boardHistory.min() ?? state.boardHeight)
        return Self(totalLengthError:totalError,maximumLocalStrain:strain,minimumSegmentClearance:clearance,minimumClearanceMargin:margin,
                    topologyValid:topology,topologyFailure:failure,maximumSpeed:speed,boardDisplacement:displacement)
    }
}
