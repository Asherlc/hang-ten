enum EvaluationAudit {
 static var evaluations=0,merits=0
 static func reset() {evaluations=0;merits=0}
}
extension RopeDynamicsSolver {
    mutating func debugEvaluation(_ candidate:RopeSimulationState)->[UInt64] {configurationEvaluation(candidate).bits}
    mutating func debugMerit(_ candidate:RopeSimulationState,prediction:RopeSimulationState,penalty:Double)throws->Double {
        var weights:[[Double]]=[]
        for rope in candidate.ropes {
            weights.append(rope.positions.indices.map {i in
                if rope.supports[i] != nil || rope.attachments[i] != nil {return 0}
                let length=(i>0 ? rope.restLengths[i-1]:0)+(i<rope.restLengths.count ? rope.restLengths[i]:0)
                return 2/(rope.linearMass*length)
            })
        }
        return try merit(candidate,prediction:prediction,weights:weights,penalty:penalty)
    }
    mutating func debugWeightedMerit(_ candidate:RopeSimulationState,prediction:RopeSimulationState,factor:Double)throws->Double {
        let weights=candidate.ropes.map {rope in rope.positions.indices.map {i -> Double in
            if rope.supports[i] != nil || rope.attachments[i] != nil {return 0}
            return factor
        }}
        return try merit(candidate,prediction:prediction,weights:weights,penalty:1)
    }
}
