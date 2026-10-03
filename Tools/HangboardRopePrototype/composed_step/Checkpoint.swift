extension RopeDynamicsSolver {
    func composedCheckpoint()->[String:Any] {
        var c=bundleCheckpoint()
        c["composedResponseSquare"]=composedResponseSquare ?? lastStepDuration*lastStepDuration
        return c
    }
    static func restoreComposedReference(input:RopePhysicsInput,collider:RopeTriangleCollider,data:Data,strict:Bool) throws -> Self {
        var c=try decodeCheckpointJSON(data)
        let previous=c["composedResponseSquare"] as? Double ?? pow(c["lastStepDuration"] as! Double,2)
        guard previous.isFinite,previous>0 else {throw RopePhysicsError.invalid("invalid composed response square")}
        let factor=RopeComposedStep.h*RopeComposedStep.h/previous
        c["distanceTension"]=(c["distanceTension"] as! [[Double]]).map{$0.map{$0*factor}}
        c["extraHints"]=(c["extraHints"] as! [[String:Any]]).map {hint in
            var result=hint;result["lambda"]=(hint["lambda"] as! Double)*factor;return result
        }
        c["lastStepDuration"]=RopeComposedStep.h
        var solver=try restoreBundle(input:input,collider:collider,data:JSONSerialization.data(withJSONObject:c,options:[.sortedKeys]),strict:strict)
        solver.composedResponseSquare=RopeComposedStep.h*RopeComposedStep.h
        return solver
    }
}
