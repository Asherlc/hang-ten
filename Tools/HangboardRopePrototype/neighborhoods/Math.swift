import Foundation
import simd

struct RopeQueryNeighborhood:Sendable {
    static let halo=0.001
    static let leafCap=64
    let identity:UUID
    let low:SIMD3<Double>,high:SIMD3<Double>
    let rowRadius:Double
    let leaves:[Int]
    func covers(low:SIMD3<Double>,high:SIMD3<Double>,radius:Double,identity:UUID)->Bool {
        guard identity==self.identity,radius.bitPattern==rowRadius.bitPattern,
              radius.isFinite,radius>=0.001,radius<=0.01,leaves.count<=Self.leafCap,
              (0..<3).allSatisfy({low[$0]<=high[$0] && self.low[$0]<=self.high[$0]}),
              let motion=motionUpper(low:low,high:high) else {return false}
        // Retain the original acquisition box. Recentring without rebuilding is unsafe.
        return motion<Self.halo-2e-9
    }
    func motionUpper(low:SIMD3<Double>,high:SIMD3<Double>)->Double? {
        guard [self.low,self.high,low,high].allSatisfy({$0.x.isFinite && $0.y.isFinite && $0.z.isFinite && max(abs($0.x),max(abs($0.y),abs($0.z)))<=0.5}) else {return nil}
        var sum=0.0
        for i in 0..<3 {
            let a=low[i]-self.low[i],b=high[i]-self.high[i]
            let component=max(max(abs(a.nextDown),abs(a.nextUp)),max(abs(b.nextDown),abs(b.nextUp)))
            sum=(sum+(component*component).nextUp).nextUp
        }
        let result=sqrt(sum).nextUp
        return result.isFinite ? result:nil
    }
}
func neighborhoodFixtures()throws {
    let identity=UUID(),other=UUID(),radius=0.00365,zero=SIMD3<Double>.zero
    let cache=RopeQueryNeighborhood(identity:identity,low:zero,high:zero,rowRadius:radius,leaves:[1,2])
    guard cache.covers(low:SIMD3(0.0005,0,0),high:SIMD3(0.0005,0,0),radius:radius,identity:identity),
          !cache.covers(low:SIMD3(0.001,0,0),high:SIMD3(0.001,0,0),radius:radius,identity:identity),
          !cache.covers(low:zero,high:zero,radius:radius,identity:other),
          !cache.covers(low:zero,high:zero,radius:radius.nextUp,identity:identity),
          !cache.covers(low:SIMD3(Double.nan,0,0),high:zero,radius:radius,identity:identity),
          !cache.covers(low:SIMD3(0.51,0,0),high:SIMD3(0.51,0,0),radius:radius,identity:identity) else {
        throw RopePhysicsError.invalid("neighborhood motion/binding/domain fixtures")
    }
    // Opposite endpoints can change different box corners: endpoint norm alone is unsafe.
    let old=RopeQueryNeighborhood(identity:identity,low:SIMD3(0,0,0),high:SIMD3(0.1,0.1,0),rowRadius:radius,leaves:[])
    guard let upper=old.motionUpper(low:SIMD3(-0.0008,0,0),high:SIMD3(0.1,0.1008,0)),upper>0.001,
          !old.covers(low:SIMD3(-0.0008,0,0),high:SIMD3(0.1,0.1008,0),radius:radius,identity:identity),
          !RopeQueryNeighborhood(identity:identity,low:zero,high:zero,rowRadius:radius,leaves:Array(0...64)).covers(low:zero,high:zero,radius:radius,identity:identity) else {
        throw RopePhysicsError.invalid("box corners/roster cap fixtures")
    }
    var copy=[cache];let original=copy;copy.removeAll()
    guard original.count==1 else {throw RopePhysicsError.invalid("neighborhood value copy")}
    print("PASS neighborhood box-motion/binding/domain/cap/value-copy fixtures")
}
