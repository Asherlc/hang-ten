import simd
enum RopeArmijo {
    static let sigma=0.1
    static func lengthSlope(residual:Double,rate:Double)->Double {
        residual>0 ? rate:(residual<0 ? -rate:abs(rate))
    }
    static func inactiveHinge(_ argument:Double)->Bool {argument.isFinite && argument<0}
    static func hingeSlope(argument:Double,rate:Double)->Double {
        argument>0 ? rate:(argument<0 ? 0:max(0,rate))
    }
    static func envelopeModel(arguments:[Double],rates:[Double],alpha:Double)->Double {
        max(0,zip(arguments,rates).map{$0+alpha*$1}.max() ?? 0)
    }
    static func displacement(_ rope:RopeChainState,_ i:Int,_ correction:SIMD3<Double>,_ height:Double)->SIMD3<Double> {
        if rope.supports[i] != nil {return .zero}
        if rope.attachments[i] != nil {return SIMD3(0,height,0)}
        return correction
    }
}
