import Foundation
import simd
import Darwin
func bits(_ v:SIMD3<Double>)->[UInt64] {[v.x.bitPattern,v.y.bitPattern,v.z.bitPattern]}
func signature(_ h:RopeSegmentContact)->[UInt64] {
    bits(h.centerlinePoint)+bits(h.surfacePoint)+bits(h.normal)+[h.fraction.bitPattern,h.penetrationDepth.bitPattern,h.timeOfImpact?.bitPattern ?? UInt64.max]
}
func surface(_ h:RopeSurfaceContact)->[UInt64] {bits(h.point)+bits(h.normal)+[h.distance.bitPattern]}
func vec(_ a:[Double])->SIMD3<Double> {SIMD3(a[0],a[1],a[2])}
let descriptor=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))
let raw=try JSONSerialization.jsonObject(with:descriptor) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(descriptor).validated(modelSHA256:raw["modelSHA256"] as! String)
let reference=try ReferenceTriangleCollider(input:input),candidate=try RopeTriangleCollider(input:input)
let captured=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]))) as! [String:Any]
var queries=(captured["queries"] as! [[String:Any]]).map {q in (vec(q["a"] as! [Double]),vec(q["b"] as! [Double]),q["radius"] as! Double)}
// Exact triangle interiors, both sides, vertices, edge endpoints, zero-length and crossing links.
for id in stride(from:0,to:input.collision.triangles.count,by:137) {
    let f=input.collision.triangles[id],a=input.collision.vertices[f.x],b=input.collision.vertices[f.y],c=input.collision.vertices[f.z]
    let center=(a+b+c)/3,n=simd_normalize(simd_cross(b-a,c-a))
    queries += [(center,center,0.00365),(a,b,0.00365),(center-n*0.000001,center+n*0.000001,0.00365),
        (center-n*0.000001,center-n*0.000001,0.00365),(center+n*0.000001,center+n*0.000001,0.00365)]
}
alarm(30)
var missingContactRed=false,insideSignRed=false
for (i,q) in queries.enumerated() {
    let (a,b,r)=q
    let x=reference.segmentContacts(from:a,to:b,radius:r).map(signature),y=candidate.segmentContacts(from:a,to:b,radius:r).map(signature)
    guard x==y,
          reference.signedDistance(at:a).bitPattern==candidate.signedDistance(at:a).bitPattern,
          reference.segmentClearance(from:a,to:b).bitPattern==candidate.segmentClearance(from:a,to:b).bitPattern,
          surface(reference.closestSurface(at:a))==surface(candidate.closestSurface(at:a)),
          reference.segmentContact(from:a,to:b,radius:r).map(signature)==candidate.segmentContact(from:a,to:b,radius:r).map(signature),
          reference.queryParity(a)==candidate.queryParity(a) else {throw RopePhysicsError.invalid("Query identity failed at \(i)")}
    if !x.isEmpty {missingContactRed = missingContactRed || x != Array(y.dropLast())}
    if reference.queryParity(a) {insideSignRed = insideSignRed || reference.signedDistance(at:a).bitPattern != (-candidate.signedDistance(at:a)).bitPattern}
}
alarm(0)
guard missingContactRed,insideSignRed else {throw RopePhysicsError.invalid("Negative control failed")}
print("PASS",queries.count,"queries: all Double bits, parity and contact witnesses identical; missing-contact and altered-inside-sign controls rejected")
