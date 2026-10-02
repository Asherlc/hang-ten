import Foundation

/// Fixed central derivative of a contact gradient. Experimental, not app code.
enum NonlinearContactCurvature {
    static func hessian(count:Int,minimumRest:Double,gradient:(Int,Double)throws->[Double]) throws -> (matrix:[[Double]],raw:[[Double]],asymmetry:Double) {
        guard (1...13).contains(count),minimumRest.isFinite,minimumRest>0 else {
            throw RopePhysicsError.invalid("Invalid contact curvature stencil")
        }
        let step=cbrt(Double.ulpOfOne)*minimumRest
        guard step.isFinite,step>0 else {throw RopePhysicsError.invalid("Nonfinite contact curvature step")}
        var raw=Array(repeating:Array(repeating:0.0,count:count),count:count)
        for axis in 0..<count {
            let plus=try gradient(axis,step),minus=try gradient(axis,-step)
            guard plus.count==count,minus.count==count,(plus+minus).allSatisfy({$0.isFinite}) else {
                throw RopePhysicsError.invalid("Invalid contact curvature gradients")
            }
            for row in 0..<count {raw[row][axis]=(plus[row]-minus[row])/(2*step)}
        }
        var matrix=raw,asymmetry=0.0
        for row in 0..<count {for column in 0..<count {
            asymmetry=max(asymmetry,abs(raw[row][column]-raw[column][row]))
            matrix[row][column]=0.5*(raw[row][column]+raw[column][row])
        }}
        guard matrix.flatMap({$0}).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite contact curvature matrix")}
        return (matrix,raw,asymmetry)
    }
}
