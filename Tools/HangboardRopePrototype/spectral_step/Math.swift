import Foundation

enum RopeSpectralStep {
    static func relaxation(point:[Double],previousPoint:[Double],direction:[Double],previousDirection:[Double])->Double? {
        guard point.count==previousPoint.count,point.count==direction.count,
              point.count==previousDirection.count,!point.isEmpty else {return nil}
        var numerator=0.0,denominator=0.0
        for i in point.indices {
            let s=point[i]-previousPoint[i],y=direction[i]-previousDirection[i]
            guard s.isFinite,y.isFinite else {return nil}
            numerator += s*y;denominator += y*y
        }
        guard numerator.isFinite,denominator.isFinite,denominator>0 else {return nil}
        let omega = -numerator/denominator
        return omega.isFinite && omega>0 && omega<1 ? omega:nil
    }
}
func spectralFixtures()throws {
    // d(x)=-2.5*x: an undamped iteration overshoots; inverse secant recovers .4.
    let value=RopeSpectralStep.relaxation(point:[-1.5],previousPoint:[1],direction:[3.75],previousDirection:[-2.5])
    guard let value,abs(value-0.4)<1e-14 else {throw RopePhysicsError.invalid("spectral overshooting mode")}
    guard RopeSpectralStep.relaxation(point:[1],previousPoint:[0],direction:[1],previousDirection:[1])==nil,
        RopeSpectralStep.relaxation(point:[1],previousPoint:[0],direction:[2],previousDirection:[1])==nil,
        RopeSpectralStep.relaxation(point:[Double.nan],previousPoint:[0],direction:[2],previousDirection:[1])==nil else {
        throw RopePhysicsError.invalid("spectral undefined/noncontracting guard")
    }
    print("PASS spectral fixtures: overshoot inverse secant, undefined/noncontracting guards")
}
