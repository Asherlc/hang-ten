import Foundation
// Snapshot-only SQP iteration matrix rule, not a material-stiffness change.
enum RopeMassOnly {
    static func stiffness(_ original:Double,enabled:Bool)throws->Double {
        guard original.isFinite,original>=0 else {throw RopePhysicsError.invalid("mass-only stiffness input")}
        return enabled ? 0:original
    }
}
func massOnlyFixtures()throws {
    guard try RopeMassOnly.stiffness(2.5,enabled:false)==2.5,
          try RopeMassOnly.stiffness(2.5,enabled:true)==0,
          try RopeMassOnly.stiffness(0,enabled:true)==0 else {throw RopePhysicsError.invalid("mass-only candidate Hessian rule")}
    for input in [-1.0,Double.nan,Double.infinity] {
        var rejected=false
        do {_ = try RopeMassOnly.stiffness(input,enabled:true)} catch RopePhysicsError.invalid {rejected=true}
        guard rejected else {throw RopePhysicsError.invalid("mass-only invalid rule input")}
    }
    print("PASS mass-only numerical Hessian/disabled/input fixtures")
}
