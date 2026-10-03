import Foundation
enum ArmijoTrace {
    static var corrections:[[String:Any]]=[]
    // Native driver changes this only before/after fully joined solver calls.
    static var collectDerivatives=false
    static var collectOracleBranches=false
    static var derivativeFailures:[[String:Any]]=[]
    static var slopeDetails:[[String:Any]]=[]
}
