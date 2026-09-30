import simd

/// Contact between distinct material chains, including their swept motion.
/// A shared support represents a joined knot, not a license for the exterior
/// spans to overlap. Split links at the fixed material boundary of that knot.
enum RopeCordContacts {
    struct Contact:Sendable {
        let firstSegment:Int
        let secondSegment:Int
        let firstFraction:Double
        let secondFraction:Double
        let normal:SIMD3<Double>
        let distance:Double
        let targetDistance:Double
    }
    private struct Piece {
        let segment:Int
        var lower:Double
        var upper:Double
        let knot:SIMD3<Double>?
        func start(_ rope:RopeChainState)->SIMD3<Double> {
            rope.positions[segment]+(rope.positions[segment+1]-rope.positions[segment])*lower
        }
        func end(_ rope:RopeChainState)->SIMD3<Double> {
            rope.positions[segment]+(rope.positions[segment+1]-rope.positions[segment])*upper
        }
    }

    private static func pieces(_ rope:RopeChainState,joinedTo other:RopeChainState)->[Piece] {
        var arc=[0.0]
        for length in rope.restLengths {arc.append(arc.last!+length)}
        let joined=rope.supports.keys.sorted().filter {i in
            other.supports.values.contains {simd_distance(rope.supports[i]!,$0)<1e-10}
        }
        var result:[Piece]=[]
        for i in rope.restLengths.indices {
            var cuts=[0.0,1.0]
            for support in joined {
                for boundary in [arc[support]-4*rope.radius,arc[support]+4*rope.radius] {
                    let fraction=(boundary-arc[i])/rope.restLengths[i]
                    if fraction>1e-10 && fraction<1-1e-10 {cuts.append(fraction)}
                }
            }
            cuts.sort()
            for (lo,hi) in zip(cuts,cuts.dropFirst()) where hi-lo>1e-10 {
                let material=arc[i]+(lo+hi)/2*rope.restLengths[i]
                let knot=joined.first {abs(material-arc[$0])<4*rope.radius}.flatMap {rope.supports[$0]}
                result.append(Piece(segment:i,lower:lo,upper:hi,knot:knot))
            }
        }
        return result
    }

    private static func sameKnot(_ a:Piece,_ b:Piece)->Bool {
        guard let first=a.knot,let second=b.knot else{return false}
        return simd_distance(first,second)<1e-10
    }

    private static func separated(_ a:SIMD3<Double>,_ b:SIMD3<Double>,
                                  _ c:SIMD3<Double>,_ d:SIMD3<Double>,radius:Double)->Bool {
        let low=simd_min(a,b),high=simd_max(a,b),otherLow=simd_min(c,d),otherHigh=simd_max(c,d)
        let gap=simd_max(simd_max(low-otherHigh,otherLow-high),SIMD3(repeating:0))
        return simd_length_squared(gap)>=radius*radius
    }

    private static func trimSupportEndpoint(_ original:Piece,rope:RopeChainState,support:SIMD3<Double>)->Piece {
        var piece=original
        let fraction=min(piece.upper-piece.lower,1e-6/rope.restLengths[piece.segment])
        if simd_distance(piece.start(rope),support)<1e-10 {piece.lower += fraction}
        if simd_distance(piece.end(rope),support)<1e-10 {piece.upper -= fraction}
        return piece
    }

    static func between(_ first:RopeChainState,_ second:RopeChainState,margin:Double=0)->[Contact] {
        let aPieces=pieces(first,joinedTo:second),bPieces=pieces(second,joinedTo:first)
        var result:[Contact]=[]
        for originalA in aPieces {
            for originalB in bPieces {
                var aPiece=originalA,bPiece=originalB
                let knot=sameKnot(aPiece,bPiece)
                if knot,let support=aPiece.knot {
                    aPiece=trimSupportEndpoint(aPiece,rope:first,support:support)
                    bPiece=trimSupportEndpoint(bPiece,rope:second,support:support)
                }
                let a=aPiece.start(first),b=aPiece.end(first),c=bPiece.start(second),d=bPiece.end(second)
                let threshold=knot ? 1e-8:first.radius+second.radius-0.00005+margin
                if separated(a,b,c,d,radius:threshold) {continue}
                let witness=RopeTriangleCollider.segmentPair(a,b,c,d)
                let delta=witness.0-witness.1,distance=simd_length(delta)
                guard distance<threshold else{continue}
                let g=simd_length_squared(d-c)>1e-20
                    ? min(1,max(0,simd_dot(witness.1-c,d-c)/simd_length_squared(d-c))):0
                var normal=distance>1e-10 ? delta/distance:simd_cross(b-a,d-c)
                normal=simd_length(normal)>1e-10 ? simd_normalize(normal):SIMD3(1,0,0)
                result.append(Contact(firstSegment:aPiece.segment,secondSegment:bPiece.segment,
                    firstFraction:aPiece.lower+(aPiece.upper-aPiece.lower)*witness.2,
                    secondFraction:bPiece.lower+(bPiece.upper-bPiece.lower)*g,normal:normal,distance:distance,
                    targetDistance:knot ? 1e-8:first.radius+second.radius+0.00005))
            }
        }
        return result
    }

    static func sweepValid(previousFirst:RopeChainState,first:RopeChainState,
                           previousSecond:RopeChainState,second:RopeChainState)->Bool {
        guard previousFirst.restLengths==first.restLengths,previousSecond.restLengths==second.restLengths else{return false}
        let aPieces=pieces(first,joinedTo:second),bPieces=pieces(second,joinedTo:first)
        for originalA in aPieces {
            for originalB in bPieces {
                var aPiece=originalA,bPiece=originalB
                let knot=sameKnot(aPiece,bPiece)
                if knot,let support=aPiece.knot {
                    // Trim the coincident mathematical support endpoint only.
                    // All other centerline crossings inside the knot are tested.
                    aPiece=trimSupportEndpoint(aPiece,rope:first,support:support)
                    bPiece=trimSupportEndpoint(bPiece,rope:second,support:support)
                }
                let a=aPiece.start(previousFirst),b=aPiece.end(previousFirst),c=bPiece.start(previousSecond),d=bPiece.end(previousSecond)
                let nextA=aPiece.start(first),nextB=aPiece.end(first),nextC=bPiece.start(second),nextD=bPiece.end(second)
                let threshold=knot ? 1e-8:first.radius+second.radius-0.00005
                let low=simd_min(simd_min(a,b),simd_min(nextA,nextB)),high=simd_max(simd_max(a,b),simd_max(nextA,nextB))
                let otherLow=simd_min(simd_min(c,d),simd_min(nextC,nextD)),otherHigh=simd_max(simd_max(c,d),simd_max(nextC,nextD))
                let gap=simd_max(simd_max(low-otherHigh,otherLow-high),SIMD3(repeating:0))
                if simd_length_squared(gap)>=threshold*threshold {continue}
                let motion=max(simd_distance(a,nextA),simd_distance(b,nextB))+max(simd_distance(c,nextC),simd_distance(d,nextD))
                var t=0.0,certified=false
                for _ in 0..<256 {
                    let pair=RopeTriangleCollider.segmentPair(a+(nextA-a)*t,b+(nextB-b)*t,c+(nextC-c)*t,d+(nextD-d)*t)
                    let clearance=simd_distance(pair.0,pair.1)-threshold
                    if clearance<=1e-9 {return false}
                    if motion<1e-12 || t>=1 {certified=true;break}
                    t=min(1,t+0.8*clearance/motion)
                }
                // Reaching the endpoint on the last advancement still needs
                // the same clearance check as reaching it one iteration sooner.
                if !certified && t>=1 {
                    let pair=RopeTriangleCollider.segmentPair(nextA,nextB,nextC,nextD)
                    certified=simd_distance(pair.0,pair.1)-threshold>1e-9
                }
                if !certified {return false}
            }
        }
        return true
    }
}
