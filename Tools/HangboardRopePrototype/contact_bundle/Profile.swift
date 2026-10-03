// Native driver only. Joined wall times, no timers inside parallel face kernels.
enum RopeBundleCensus {
    static var enabled=false
    static var keys:[[UInt64]:Int]=[:]
    static var events:[[String:Any]]=[]
    static var reason="changed geometry"
    static func reset() {keys=[:];events=[];reason="changed geometry";AcceptedSolverProfile.buckets=[:]}
    static func invalidate(_ value:String) {if enabled {reason=value}}
    static func wood(_ seconds:Double) {
        guard enabled,!events.isEmpty else {return}
        let index=events.count-1
        events[index]["woodSeconds"]=(events[index]["woodSeconds"] as? Double ?? 0)+seconds
    }
    static func build(_ state:RopeSimulationState,epoch:Int) {
        guard enabled else {return}
        var bits=[state.boardHeight.bitPattern,state.orientation.vector.x.bitPattern,state.orientation.vector.y.bitPattern,
            state.orientation.vector.z.bitPattern,state.orientation.vector.w.bitPattern]
        for rope in state.ropes {
            bits += [UInt64(rope.positions.count),rope.radius.bitPattern]
            for p in rope.positions {bits += [p.x.bitPattern,p.y.bitPattern,p.z.bitPattern]}
        }
        let previous=keys[bits],id=previous ?? keys.count
        keys[bits]=id
        events.append(["key":id,"epoch":epoch,"repeated":previous != nil,"reason":reason,
            "caller":AcceptedSolverProfile.stack.map(\.name).joined(separator:"/")])
        reason="changed geometry"
    }
}
