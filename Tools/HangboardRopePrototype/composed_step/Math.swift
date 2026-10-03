import Foundation
import simd

enum RopeComposedStep {
    static let h=1.0/240
    static let damping=exp(-18*h)
    static let responseSquare=h*h*(2+damping)
    static let velocityCoefficient=(1+damping)/(2+damping)
    static let arrivalLimit=0.001*h/velocityCoefficient
    static func velocities(_ old:SIMD3<Double>)->(SIMD3<Double>,SIMD3<Double>) {
        let first=(old+SIMD3(0,-9.81*h,0))*damping
        return (first,(first+SIMD3(0,-9.81*h,0))*damping)
    }
    static func heights(_ old:Double)->(Double,Double) {
        let first=(old-9.81*h)*damping
        return (first,(first-9.81*h)*damping)
    }
}
