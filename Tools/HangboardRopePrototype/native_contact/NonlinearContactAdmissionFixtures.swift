import Foundation
import Darwin
do {
    let cold=try NonlinearContactAdmission.initialize(residual:0.00004,scale:0.0035,coldS:7e-8,priorMeanSV:nil)
    guard cold.s==7e-8,cold.v==0.0035,cold.normalizationS==7e-8,!cold.continued else {
        throw RopePhysicsError.invalid("Cold contact initialization changed")
    }
    let late=try NonlinearContactAdmission.initialize(residual:0.00004,scale:0.0035,coldS:7e-8,priorMeanSV:1.4e-11)
    guard abs(late.s-4e-9)<1e-24,abs(late.v-(0.00004+4e-17))<1e-20,
          late.normalizationS==7e-8,late.continued,
          0.00004+1e-8*late.s-late.v==0,late.s*late.v<=1.4e-11 else {
        throw RopePhysicsError.invalid("Late positive-gap contact injects artificial slack/force or changes normalization")
    }
    print("PASS literal force budget, actual gap, zero h and immutable normalization")
    let capped=try NonlinearContactAdmission.initialize(residual:0.00004,scale:0.0035,coldS:7e-8,priorMeanSV:1e-8)
    guard capped.s==7e-8,capped.continued else {throw RopePhysicsError.invalid("Continuation exceeds original cold force")}
    for c in [-0.00001,0,0.004] {
        let v=try NonlinearContactAdmission.initialize(residual:c,scale:0.0035,coldS:7e-8,priorMeanSV:1.4e-11)
        guard v.s==7e-8,v.v==max(c+7e-16,0.0035),v.normalizationS==7e-8,!v.continued else {
            throw RopePhysicsError.invalid("Nonpositive/far gap fallback changed")
        }
    }
    print("PASS original cold start, force cap and nonpositive/far-gap fallback")
    func rejects(_ c:Double,_ scale:Double,_ cold:Double,_ mu:Double?) throws {
        do {
            _=try NonlinearContactAdmission.initialize(residual:c,scale:scale,coldS:cold,priorMeanSV:mu)
        } catch {return}
        throw RopePhysicsError.invalid("Invalid contact initializer input accepted")
    }
    try rejects(.nan,0.0035,7e-8,1e-11)
    try rejects(0.00004,0,7e-8,1e-11)
    try rejects(0.00004,0.0035,0,1e-11)
    try rejects(0.00004,0.0035,7e-8,0)
    try rejects(0.00004,0.0035,7e-8,.infinity)
    try rejects(0.001,2,7e-8,Double.leastNonzeroMagnitude)
    try rejects(0.00004,0.0035,7e-8,Double.leastNonzeroMagnitude)
    print("PASS invalid/nonpositive inputs and force underflow reject without a floor")
} catch {print("FAIL",error);exit(1)}
