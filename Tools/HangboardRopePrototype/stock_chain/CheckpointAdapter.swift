extension RopeDynamicsSolver {
    func foundationCheckpoint()->[String:Any] {
        func v(_ x:SIMD3<Double>)->[Double] {[x.x,x.y,x.z]}
        func crossing(_ c:RopePortalCrossing)->[String:Any] {["segment":c.segment,"fraction":c.fraction]}
        func points(_ p:[Int:SIMD3<Double>])->[String:[Double]] {Dictionary(uniqueKeysWithValues:p.map{(String($0.key),v($0.value))})}
        let ropes:[[String:Any]]=state.ropes.map {p in
            ["id":p.id,"radius":p.radius,"linearMass":p.linearMass,"restLengths":p.restLengths,
             "positions":p.positions.map(v),"previousPositions":p.previousPositions.map(v),"velocities":p.velocities.map(v),
             "supports":points(p.supports),"attachments":points(p.attachments),
             "portals":Dictionary(uniqueKeysWithValues:p.portals.map{(String($0.key),$0.value)}),
             "channelSegments":Dictionary(uniqueKeysWithValues:p.channelSegments.map{(String($0.key),$0.value)}),
             "portalCrossings":p.portalCrossings.mapValues(crossing),
             "channelSpans":p.channelSpans.mapValues{["start":crossing($0.start),"end":crossing($0.end)]}]
        }
        return ["profileID":state.profileID,"boardMass":state.boardMass,"boardHeight":state.boardHeight,
                "boardVerticalVelocity":state.boardVerticalVelocity,"orientation":[state.orientation.vector.x,state.orientation.vector.y,state.orientation.vector.z,state.orientation.vector.w],
                "ropes":ropes,"time":time,"history":history.map{[$0.0,$0.1]},
                "acceptedMinimumClearance":acceptedMinimumClearance as Any? ?? NSNull(),
                "distanceTension":distanceTension,"lastStepDuration":lastStepDuration]
    }
}

extension RopeDynamicsSolver {
    static func restoreFoundation(input:RopePhysicsInput,collider:RopeTriangleCollider,data:Data) throws -> Self {
        let c=try decodeCheckpointJSON(data)
        func vector(_ a:[Double])->SIMD3<Double> {SIMD3(a[0],a[1],a[2])}
        func crossing(_ a:[String:Any])->RopePortalCrossing {RopePortalCrossing(segment:a["segment"] as! Int,fraction:a["fraction"] as! Double)}
        func points(_ a:Any)->[Int:SIMD3<Double>] {Dictionary(uniqueKeysWithValues:(a as! [String:[Double]]).map{(Int($0.key)!,vector($0.value))})}
        func labels(_ a:Any)->[Int:String] {Dictionary(uniqueKeysWithValues:(a as! [String:String]).map{(Int($0.key)!,$0.value)})}
        let ropes=(c["ropes"] as! [[String:Any]]).map {p in
            RopeChainState(id:p["id"] as! String,radius:p["radius"] as! Double,linearMass:p["linearMass"] as! Double,
                restLengths:p["restLengths"] as! [Double],positions:(p["positions"] as! [[Double]]).map(vector),
                previousPositions:(p["previousPositions"] as! [[Double]]).map(vector),velocities:(p["velocities"] as! [[Double]]).map(vector),
                supports:points(p["supports"]!),attachments:points(p["attachments"]!),portals:labels(p["portals"]!),
                channelSegments:labels(p["channelSegments"]!),
                portalCrossings:(p["portalCrossings"] as! [String:[String:Any]]).mapValues(crossing),
                channelSpans:(p["channelSpans"] as! [String:[String:[String:Any]]]).mapValues{RopeChannelSpan(start:crossing($0["start"]!),end:crossing($0["end"]!))})
        }
        let q=c["orientation"] as! [Double]
        let state=RopeSimulationState(profileID:c["profileID"] as! String,boardMass:c["boardMass"] as! Double,
            boardHeight:c["boardHeight"] as! Double,boardVerticalVelocity:c["boardVerticalVelocity"] as! Double,
            orientation:simd_quatd(vector:SIMD4(q[0],q[1],q[2],q[3])),ropes:ropes)
        var solver=try Self(input:input,state:state,collider:collider)
        solver.time=c["time"] as! Double
        solver.history=(c["history"] as! [[Double]]).map{($0[0],$0[1])}
        solver.distanceTension=c["distanceTension"] as! [[Double]]
        solver.lastStepDuration=c["lastStepDuration"] as! Double
        solver.acceptedMinimumClearance=c["acceptedMinimumClearance"] as? Double
        return solver
    }
}
