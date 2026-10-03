import Foundation
import simd

// Only selected when all triangle coordinates on an axis are exactly equal.
struct RopeAxisSupport:Sendable {
    let axis:Int,coordinate:Double
    init?(_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>) {
        guard [a,b,c].allSatisfy({$0.x.isFinite && $0.y.isFinite && $0.z.isFinite}),
              let i=(0..<3).first(where:{a[$0]==b[$0] && a[$0]==c[$0]}) else {return nil}
        axis=i;coordinate=a[i]
    }
    func bound(_ a:SIMD3<Double>,_ b:SIMD3<Double>)->RopeCertifiedClearance? {
        guard a.x.isFinite,a.y.isFinite,a.z.isFinite,b.x.isFinite,b.y.isFinite,b.z.isFinite else {return nil}
        let gap=max((min(a[axis],b[axis])-coordinate).nextDown,(coordinate-max(a[axis],b[axis])).nextDown)
        return RopeCertifiedClearance(lowerBound:max(0,gap))
    }
}
func axisBoundFixtures()throws {
    let a=SIMD3<Double>(0,0,0),b=SIMD3<Double>(1,0,0),c=SIMD3<Double>(0,1,0)
    guard let plane=RopeAxisSupport(a,b,c),plane.axis==2,
          let bound=plane.bound(SIMD3(0.1,0.1,0.1),SIMD3(0.9,0.1,0.1)),bound.lowerBound<=0.1,bound.lowerBound>0.099999999,
          plane.bound(SIMD3(0.1,0.1,-0.1),SIMD3(0.1,0.1,0.1))?.lowerBound==0,
          plane.bound(SIMD3(Double.nan,0,0),SIMD3(0,0,1))==nil,
          RopeAxisSupport(a,b,SIMD3(0,1,Double.leastNormalMagnitude))==nil else {
        throw RopePhysicsError.invalid("axis support fixtures")
    }
    print("PASS axis support exact-coordinate/same-side/crossing/unknown fixtures")
}
