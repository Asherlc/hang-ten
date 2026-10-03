import Foundation
import simd

// A lower bound, never a measured or exact nearest distance.
struct RopeCertifiedClearance:Sendable {let lowerBound:Double}

struct RopeTriangleSupport:Sendable {
    let direction:SIMD3<Double>,lower:Double,upper:Double,normUpper:Double
    private static let gamma5=(5*Double.ulpOfOne/2)/(1-5*Double.ulpOfOne/2)
    static func interval(_ p:SIMD3<Double>,_ n:SIMD3<Double>)->(Double,Double) {
        let x=p.x*n.x,y=p.y*n.y,z=p.z*n.z,value=(x+y)+z
        let sum=((abs(x).nextUp+abs(y).nextUp).nextUp+abs(z).nextUp).nextUp
        let error=(gamma5*sum).nextUp+Double.leastNormalMagnitude*8
        return ((value-error).nextDown,(value+error).nextUp)
    }
    init?(_ n:SIMD3<Double>,_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>) {
        guard n != .zero,[n,a,b,c].allSatisfy({$0.x.isFinite && $0.y.isFinite && $0.z.isFinite}) else {return nil}
        direction=n
        let x=Self.interval(a,n),y=Self.interval(b,n),z=Self.interval(c,n)
        lower=min(x.0,min(y.0,z.0));upper=max(x.1,max(y.1,z.1))
        normUpper=sqrt(max(0,Self.interval(n,n).1)).nextUp
        guard lower.isFinite,upper.isFinite,normUpper.isFinite,normUpper>0 else {return nil}
    }
    init?(unionDirection n:SIMD3<Double>,vertices:[SIMD3<Double>]) {
        guard !vertices.isEmpty,n != .zero,n.x.isFinite,n.y.isFinite,n.z.isFinite,
              vertices.allSatisfy({$0.x.isFinite && $0.y.isFinite && $0.z.isFinite}) else {return nil}
        direction=n
        var lo=Double.infinity,hi = -Double.infinity
        for p in vertices {let interval=Self.interval(p,n);lo=min(lo,interval.0);hi=max(hi,interval.1)}
        lower=lo;upper=hi;normUpper=sqrt(max(0,Self.interval(n,n).1)).nextUp
        guard lower.isFinite,upper.isFinite,normUpper.isFinite,normUpper>0 else {return nil}
    }
    func bound(_ start:SIMD3<Double>,_ end:SIMD3<Double>)->RopeCertifiedClearance? {
        guard [start,end].allSatisfy({$0.x.isFinite && $0.y.isFinite && $0.z.isFinite}) else {return nil}
        let x=Self.interval(start,direction),y=Self.interval(end,direction)
        let gap=max((min(x.0,y.0)-upper).nextDown,(lower-max(x.1,y.1)).nextDown)
        let value=max(0,(gap/normUpper).nextDown)
        guard value.isFinite else {return nil}
        return RopeCertifiedClearance(lowerBound:value)
    }
}
func unionSupportFixtures()throws {
    let vertices=[SIMD3<Double>(0,0,0),SIMD3<Double>(1,0,0),SIMD3<Double>(0,1,0),SIMD3<Double>(2,2,0.01)]
    guard let union=RopeTriangleSupport(unionDirection:SIMD3(0,0,1),vertices:vertices),
          let bound=union.bound(SIMD3(0.1,0.1,0.1),SIMD3(0.9,0.1,0.1)),
          bound.lowerBound<=0.09,bound.lowerBound>0.089999999,
          union.bound(SIMD3(0,0,0.005),SIMD3(0,0,0.005))?.lowerBound==0,
          RopeTriangleSupport(unionDirection:SIMD3(0,0,1),vertices:[])==nil else {
        throw RopePhysicsError.invalid("union support fixtures")
    }
    print("PASS union supports include every vertex, interior slab and empty fallback")
}
func clearanceBoundFixtures()throws {
    let a=SIMD3<Double>(0,0,0),b=SIMD3<Double>(1,0,0),c=SIMD3<Double>(0,1,0)
    guard let support=RopeTriangleSupport(SIMD3(0,0,7),a,b,c),
          let positive=support.bound(SIMD3(0.1,0.1,0.1),SIMD3(0.9,0.1,0.1)),
          positive.lowerBound<=0.1,positive.lowerBound>0.099999999,
          let negative=support.bound(SIMD3(0.1,0.1,-0.1),SIMD3(0.9,0.1,-0.1)),
          negative.lowerBound<=0.1,negative.lowerBound>0.099999999,
          support.bound(SIMD3(0.1,0.1,-0.1),SIMD3(0.1,0.1,0.1))?.lowerBound==0,
          support.bound(SIMD3(Double.nan,0,0),SIMD3(0,0,1))==nil,
          RopeTriangleSupport(.zero,a,b,c)==nil else {throw RopePhysicsError.invalid("support lower-bound fixtures")}
    // Worst stated BVH squared-distance allowance is below the 1 nm guard.
    let r=0.001,allowance=32*Double.ulpOfOne
    guard sqrt(r*r-allowance)>r-1e-9 else {throw RopePhysicsError.invalid("BVH radius/domain guard")}
    print("PASS support lower bounds, same-side/crossing, unknown, BVH guard fixtures")
}
