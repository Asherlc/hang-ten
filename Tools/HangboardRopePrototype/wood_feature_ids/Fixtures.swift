import Foundation
import simd
func woodFeatureFixtures()throws {
    func key(_ id:Int,_ f:SIMD3<Int>,_ source:Int,_ s:Double=0.5)->String? {WoodFeatureIdentity.key(faceID:id,face:f,source:source,fraction:s)}
    // Actual frozen Clavellium topology. Adjacent triangles encode the SAME oriented-reversed edge.
    guard key(5042,SIMD3(2439,2667,2669),408)==key(5041,SIMD3(2439,2665,2667),608),
        key(5257,SIMD3(2548,2550,2568),408)==key(5256,SIMD3(2548,2549,2550),608),
        key(5042,SIMD3(2439,2667,2669),408)=="e/2439/2667/rope/2" else {
        throw NSError(domain:"shared native wood edge identity",code:1)
    }
    guard key(1,SIMD3(10,11,12),100,0)=="v/10/rope/0",
        key(2,SIMD3(13,10,14),101,0)=="v/10/rope/0",
        key(1,SIMD3(10,11,12),102,0)=="e/10/11/rope/0",
        key(2,SIMD3(11,10,14),102,0)=="e/10/11/rope/0",
        key(1,SIMD3(10,11,12),106,0) != key(2,SIMD3(10,11,12),106,0),
        key(1,SIMD3(10,11,12),408) != key(1,SIMD3(10,13,12),408),
        key(1,SIMD3(10,11,12),407)==nil,
        key(1,SIMD3(10,11,12),435)==nil,
        key(1,SIMD3(10,11,12),300)==nil,
        key(1,SIMD3(10,11,12),408,Double.nan)==nil else {
        throw NSError(domain:"native wood feature boundaries and unknowns",code:1)
    }
}
