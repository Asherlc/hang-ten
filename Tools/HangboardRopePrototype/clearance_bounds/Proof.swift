import Foundation
import simd

enum RopePhysicsError:Error {case invalid(String)}
var generator:UInt64=0x745a9321
func random()->Double {generator=generator &* 6364136223846793005 &+ 1442695040888963407;return Double(generator>>11)/9007199254740992}
func point()->SIMD3<Double> {SIMD3(random()-0.5,random()-0.5,random()-0.5)}
func bits(_ x:Double)->String {String(x.bitPattern,radix:16)}
func bits(_ x:SIMD3<Double>)->[String] {[bits(x.x),bits(x.y),bits(x.z)]}
try clearanceBoundFixtures();try axisBoundFixtures()
var records:[[String:Any]]=[]
for i in 0..<10000 {
    let a=point(),b=point(),c=point(),p=point(),q=point()
    let n=i%2==0 ? simd_cross(b-a,c-a):point()
    guard let support=RopeTriangleSupport(n,a,b,c),let bound=support.bound(p,q) else {throw RopePhysicsError.invalid("proof input")}
    records.append(["kind":"support","vertices":[bits(a),bits(b),bits(c)],"start":bits(p),"end":bits(q),"n":bits(n),
        "lower":bits(support.lower),"upper":bits(support.upper),"normUpper":bits(support.normUpper),"bound":bits(bound.lowerBound)])
    var aa=a,bb=b,cc=c,pp=p,qq=q
    let axis=i%3;bb[axis]=aa[axis];cc[axis]=aa[axis]
    if i%2==0 {pp[axis]=aa[axis]+0.1;qq[axis]=aa[axis]+0.2}
    let axisSupport=RopeAxisSupport(aa,bb,cc)!,axisBound=axisSupport.bound(pp,qq)!
    records.append(["kind":"axis","axis":axisSupport.axis,"coordinate":bits(axisSupport.coordinate),
        "start":bits(pp),"end":bits(qq),"bound":bits(axisBound.lowerBound)])
    let low=simd_min(a,b),high=simd_max(a,b),linkLow=simd_min(p,q),linkHigh=simd_max(p,q)
    let gap=simd_max(simd_max(low-linkHigh,linkLow-high),SIMD3<Double>(repeating:0))
    let radius=0.001+random()*0.009,square=simd_length_squared(gap)
    records.append(["kind":"bvh","low":bits(low),"high":bits(high),"start":bits(p),"end":bits(q),
        "radius":bits(radius),"pruned":square>=radius*radius,"floor":bits((radius-1e-9).nextDown)])
}
try JSONSerialization.data(withJSONObject:records,options:[.sortedKeys]).write(to:URL(fileURLWithPath:CommandLine.arguments[1]))
print("PASS exported",records.count,"directed bounds and BVH cases")
