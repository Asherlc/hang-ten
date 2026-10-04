import Foundation
import simd
enum FloatFaceReject {
    // Float proposes only a direction; no Float distance ever accepts geometry.
    static func separates(_ s:SIMD3<Double>,_ t:SIMD3<Double>,_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ c:SIMD3<Double>,_ radius:Double)->Bool {
        let p=SIMD3<Float>((s+t)*0.5),q=closest(p,SIMD3<Float>(a),SIMD3<Float>(b),SIMD3<Float>(c))
        let n=SIMD3<Double>(p-q)
        guard let certificate=RopeSeparationHint(n,a,b,c) else {return false}
        return certificate.separates(s,t,radius)
    }
// FLOAT_CLOSEST
}
func floatFaceFixtures()throws {
    let a=SIMD3<Double>(0,0,0),b=SIMD3<Double>(1,0,0),c=SIMD3<Double>(0,1,0)
    guard FloatFaceReject.separates(SIMD3(0.1,0.1,0.1),SIMD3(0.9,0.1,0.1),a,b,c,0.0035),
          !FloatFaceReject.separates(SIMD3(0.1,0.1,0.0035),SIMD3(0.9,0.1,0.0035),a,b,c,0.0035),
          !FloatFaceReject.separates(SIMD3(0.1,0.1,-0.1),SIMD3(0.1,0.1,0.1),a,b,c,0.0035),
          !FloatFaceReject.separates(SIMD3(Double.nan,0,0),SIMD3(0,0,0.1),a,b,c,0.0035),
          !FloatFaceReject.separates(SIMD3(0.1,0.1,0),SIMD3(0.1,0.1,0),a,b,c,0.0035) else {
        throw RopePhysicsError.invalid("Float direction/fresh Double whole-capsule fixtures")
    }
}
