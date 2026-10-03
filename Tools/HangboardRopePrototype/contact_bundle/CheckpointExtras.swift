// Native adapters preserve original warm hints and per-link CCD receipts, too.
extension RopeDynamicsSolver {
    func bundleCheckpoint()->[String:Any] {
        var result=foundationCheckpoint()
        result["extraBounds"]=acceptedSegmentClearanceBounds?.map{$0.map{String($0.bitPattern,radix:16)}} as Any? ?? NSNull()
        result["extraFullStep"]=lastCorrectionFullStep
        result["extraHints"]=contactHints.map{row,lambda in ["indices":row.indices,"coefficients":row.coefficients,
            "border":row.border,"residual":row.residual,"lambda":lambda] as [String:Any]}
        return result
    }
    static func restoreBundle(input:RopePhysicsInput,collider:RopeTriangleCollider,data:Data,strict:Bool=false) throws -> Self {
        var solver=try restoreFoundation(input:input,collider:collider,data:data)
        let c=try decodeCheckpointJSON(data)
        solver.acceptedSegmentClearanceBounds=(c["extraBounds"] as? [[String]])?.map{$0.map{Double(bitPattern:UInt64($0,radix:16)!)}}
        solver.lastCorrectionFullStep=c["extraFullStep"] as! Bool
        solver.contactHints=(c["extraHints"] as! [[String:Any]]).map {row in
            (RopeLinearContact(indices:row["indices"] as! [Int],coefficients:row["coefficients"] as! [Double],
                border:row["border"] as! [Double],residual:row["residual"] as! Double),row["lambda"] as! Double)
        }
        if strict {solver.convergenceExperiment=false}
        return solver
    }
}
