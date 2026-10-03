private struct RopeConfigurationEvaluation:Sendable {
    let bits:[UInt64]
    let portalOrder:[String]
    let points:[[[RopeSegmentContact]]]
    let rows:[[[RopeSegmentContact]]]
    let merits:[[[RopeSegmentContact]]]
    let selfPairs:[[SIMD2<Int>]]
    let cordContacts:[SIMD2<Int>:[RopeCordContacts.Contact]]
    var meritParts:(Double,Double)?=nil
    var meritInputs:[UInt64]?=nil
}
extension RopeDynamicsSolver {
    private mutating func configurationEvaluation(_ candidate:RopeSimulationState)->RopeConfigurationEvaluation {
        var bits=[candidate.boardHeight.bitPattern,candidate.orientation.vector.x.bitPattern,candidate.orientation.vector.y.bitPattern,
            candidate.orientation.vector.z.bitPattern,candidate.orientation.vector.w.bitPattern]
        var portalOrder:[String]=[]
        for rope in candidate.ropes {
            bits.append(UInt64(rope.positions.count))
            for p in rope.positions {bits += [p.x.bitPattern,p.y.bitPattern,p.z.bitPattern]}
            for (id,crossing) in rope.portalCrossings {portalOrder.append(id);bits += [UInt64(crossing.segment),crossing.fraction.bitPattern]}
            portalOrder.append("/")
        }
        if let cached=cachedEvaluation,cached.bits==bits,cached.portalOrder==portalOrder {return cached}
        var points:[[[RopeSegmentContact]]]=[],rows:[[[RopeSegmentContact]]]=[],merits:[[[RopeSegmentContact]]]=[],pairs:[[SIMD2<Int>]]=[]
        for rope in candidate.ropes {
            let board=rope.positions.map{candidate.boardPoint($0)},inside=board.map{collider.queryParity($0)}
            var p=Array(repeating:[RopeSegmentContact](),count:board.count),r:[[RopeSegmentContact]]=[],m:[[RopeSegmentContact]]=[]
            for link in rope.restLengths.indices {
                let contacts=collider.fusedContacts(from:board[link],to:board[link+1],rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,
                    meritRadius:rope.radius+RopeRegionGeometry.clearance,startInside:inside[link],endInside:inside[link+1])
                p[link]=contacts[0];r.append(contacts[1]);m.append(contacts[2])
                if link==rope.restLengths.count-1 {p[link+1]=contacts[3]}
            }
            points.append(p);rows.append(r);merits.append(m)
            pairs.append(RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths))
        }
        var cords:[SIMD2<Int>:[RopeCordContacts.Contact]]=[:]
        for first in candidate.ropes.indices {for second in candidate.ropes.indices where second>first {
            cords[SIMD2(first,second)]=RopeCordContacts.between(candidate.ropes[first],candidate.ropes[second],margin:0.0001)
        }}
        let result=RopeConfigurationEvaluation(bits:bits,portalOrder:portalOrder,points:points,rows:rows,merits:merits,selfPairs:pairs,cordContacts:cords)
        cachedEvaluation=result
        return result
    }
}
