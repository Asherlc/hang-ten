import Foundation
import simd
import Darwin
let raw=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))) as! [String:Any]
let mesh=raw["collision"] as! [String:Any]
let v=(mesh["vertices"] as! [[Double]]).map{SIMD3<Double>($0[0],$0[1],$0[2])}
let f=mesh["triangles"] as! [[Int]]
var rows:[[String:Any]]=[]
func record(_ p:SIMD3<Double>,_ n:SIMD3<Double>) {
    let i=RopeTriangleProjection.interval(p,n)
    rows.append(["p":[p.x.bitPattern.description,p.y.bitPattern.description,p.z.bitPattern.description],
      "n":[n.x.bitPattern.description,n.y.bitPattern.description,n.z.bitPattern.description],"lo":i.0.bitPattern.description,"hi":i.1.bitPattern.description])
}
for face in f {
 let a=v[face[0]],b=v[face[1]],c=v[face[2]],n=simd_normalize(simd_cross(b-a,c-a))
 for d in [n,simd_normalize(simd_cross(b-a,n)),simd_normalize(simd_cross(c-b,n)),simd_normalize(simd_cross(a-c,n))] {
  record(a,d);record(b,d);record(c,d);record(d,d)
 }
}
// Cancellation and subnormal arithmetic are explicit edge cases.
for p in [SIMD3<Double>(1e-200,-1e-200,1e-200),SIMD3<Double>(1,-1,Double.leastNonzeroMagnitude),SIMD3<Double>(0.12,-0.12,1e-20)] {
 record(p,SIMD3<Double>(1,1,1))
}
try JSONSerialization.data(withJSONObject:rows).write(to:URL(fileURLWithPath:CommandLine.arguments[2]))
print(rows.count,"directed dot intervals exported")
