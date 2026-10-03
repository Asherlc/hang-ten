import Foundation
import simd

// Immutable board-local geometric ball, anchored at a known outside point.
struct RopePointFreeBall:Sendable {
    let center:SIMD3<Double>
    let radius:RopeCertifiedClearance
    init?(center:SIMD3<Double>,radius:RopeCertifiedClearance,outsideKnown:Bool) {
        guard outsideKnown,center.x.isFinite,center.y.isFinite,center.z.isFinite,
              radius.lowerBound.isFinite,radius.lowerBound>0 else {return nil}
        self.center=center;self.radius=radius
    }
    func contains(_ p:SIMD3<Double>)->Bool {
        guard let distance=distanceUpper(p) else {return false}
        return distance<radius.lowerBound
    }
    func distanceUpper(_ p:SIMD3<Double>)->Double? {
        guard p.x.isFinite,p.y.isFinite,p.z.isFinite else {return nil}
        var sum=0.0
        for i in 0..<3 {
            let value=p[i]-center[i]
            let component=max(abs(value.nextDown),abs(value.nextUp))
            sum=(sum+(component*component).nextUp).nextUp
        }
        let result=sqrt(sum).nextUp
        return result.isFinite ? result:nil
    }
}

struct RopeParityAnchor:Sendable {
    let ropeID:String
    let balls:[RopePointFreeBall?]
}
func freeBallFixtures()throws {
    let radius=RopeCertifiedClearance(lowerBound:0.0036)
    guard let ball=RopePointFreeBall(center:.zero,radius:radius,outsideKnown:true),
          ball.contains(SIMD3(0.0035,0,0)),!ball.contains(SIMD3(0.0036,0,0)),
          !ball.contains(SIMD3(Double.nan,0,0)),
          RopePointFreeBall(center:.zero,radius:radius,outsideKnown:false)==nil,
          RopePointFreeBall(center:.zero,radius:RopeCertifiedClearance(lowerBound:0),outsideKnown:true)==nil else {
        throw RopePhysicsError.invalid("free ball classification fixtures")
    }
    var original=[ball],copy=original
    copy.removeAll()
    guard original.count==1,copy.isEmpty else {throw RopePhysicsError.invalid("free ball value copy")}
    original.removeAll()
    print("PASS free-ball open-boundary/nonfinite/outside-source/value-copy fixtures")
}
