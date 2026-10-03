import Foundation

enum RopeScaledMerit {
    static func next(previous:Double,multipliers:[Double],contacts:[Bool])throws->Double {
        guard previous.isFinite,previous>=0,multipliers.count==contacts.count,
              multipliers.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("invalid merit multiplier scale")}
        var equalityMax=0.0,contactSum=0.0
        for (lambda,contact) in zip(multipliers,contacts) {
            if contact {contactSum += abs(lambda)} else {equalityMax=max(equalityMax,abs(lambda))}
        }
        let result=max(previous,2*max(equalityMax,contactSum))
        guard result.isFinite else {throw RopePhysicsError.invalid("nonfinite merit penalty")}
        return result
    }
}
func scaledMeritFixtures()throws {
    let mass=0.01,px=1.0001,py=0.01
    let before=0.5*mass*((1-px)*(1-px)+py*py)
    let afterObjective=0.5*mass*(1-px)*(1-px),afterViolation=hypot(1,py)-1
    guard afterObjective+afterViolation>before else {throw RopePhysicsError.invalid("unit-floor negative control")}
    let rho=try RopeScaledMerit.next(previous:0,multipliers:[mass*(px-1)],contacts:[false])
    guard afterObjective+rho*afterViolation<before else {throw RopePhysicsError.invalid("scaled merit rejects improving curved equality tangent")}
    let grouped=try RopeScaledMerit.next(previous:0,multipliers:[-0.0001,0.0002,-0.0003,0.0004],contacts:[false,false,true,true])
    guard abs(grouped-0.0014)<1e-16 else {throw RopePhysicsError.invalid("grouped-contact multiplier bound")}
    let retained=try RopeScaledMerit.next(previous:grouped,multipliers:[0.0001],contacts:[false])
    let reset=try RopeScaledMerit.next(previous:0,multipliers:[0.0001],contacts:[false])
    guard retained==grouped,reset==0.0002 else {throw RopePhysicsError.invalid("step envelope/reset")}
    print("PASS scaled-merit fixtures: unit-floor RED, curved equality GREEN, grouped dual bound, envelope/reset")
}
