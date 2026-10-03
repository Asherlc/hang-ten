import Foundation
import simd

// Fixed-size stack value. A cache belongs to exactly one segment query.
struct RopePlaneBoundCache {
    private let start:SIMD3<Double>,end:SIMD3<Double>
    private var keys=SIMD8<Int32>(repeating:-1)
    private var values=SIMD8<Double>(repeating:.nan)
    init(start:SIMD3<Double>,end:SIMD3<Double>) {self.start=start;self.end=end}
    mutating func value(id:Int,support:RopeTriangleSupport?)->RopeCertifiedClearance? {
        guard id>=0,id<=Int(Int32.max) else {return nil}
        let slot=id & 7,key=Int32(id)
        if keys[slot]==key {return values[slot].isFinite ? RopeCertifiedClearance(lowerBound:values[slot]):nil}
        let result=support?.bound(start,end)
        keys[slot]=key;values[slot]=result?.lowerBound ?? .nan
        return result
    }
}
func planeCacheFixtures()throws {
    let a=SIMD3<Double>(0,0,0),b=SIMD3<Double>(1,0,0),c=SIMD3<Double>(0,1,0),p=SIMD3<Double>(0.1,0.1,0.1)
    let first=RopeTriangleSupport(SIMD3(0,0,1),a,b,c),second=RopeTriangleSupport(SIMD3(0,0,1),a+p,b+p,c+p)
    var cache=RopePlaneBoundCache(start:p,end:p)
    let x=cache.value(id:0,support:first),collision=cache.value(id:8,support:second),y=cache.value(id:0,support:first)
    guard let x,let collision,let y,x.lowerBound>0.099999999,collision.lowerBound==0,
          x.lowerBound.bitPattern==y.lowerBound.bitPattern,
          cache.value(id:0,support:first)?.lowerBound.bitPattern==x.lowerBound.bitPattern,
          cache.value(id:1,support:nil)==nil,cache.value(id:1,support:nil)==nil,
          cache.value(id:-1,support:first)==nil else {throw RopePhysicsError.invalid("plane cache collision/nil fixtures")}
    print("PASS fixed plane cache collision, query binding and unknown fixtures")
}
