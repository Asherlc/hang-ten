import Foundation
import simd

/// Direct rational aperture Hessian at a valid unclamped current crossing.
enum NonlinearPortalCurvature {
    static func hessian(a:SIMD3<Double>,b:SIMD3<Double>,center:SIMD3<Double>,normal:SIMD3<Double>,inward:SIMD3<Double>,
                        da:[SIMD3<Double>],db:[SIMD3<Double>]) throws -> [[Double]] {
        let d=simd_dot(normal,b-a),u=simd_dot(normal,center-a)
        guard da.count==db.count,(1...13).contains(da.count),abs(d)>1e-12,(u/d).isFinite,u/d>=0,u/d<=1 else {
            throw RopePhysicsError.invalid("Invalid current unclamped portal Hessian")
        }
        let e=simd_dot(inward,b-a),n=u*e
        let du=da.map{-simd_dot(normal,$0)},dd=zip(da,db).map{simd_dot(normal,$0.1-$0.0)},de=zip(da,db).map{simd_dot(inward,$0.1-$0.0)}
        let dn=da.indices.map{du[$0]*e+u*de[$0]}
        var matrix=Array(repeating:Array(repeating:0.0,count:da.count),count:da.count)
        for i in da.indices {for j in 0...i {
            let d2n=du[i]*de[j]+du[j]*de[i]
            let value=d2n/d-(dn[i]*dd[j]+dn[j]*dd[i])/(d*d)+2*n*dd[i]*dd[j]/(d*d*d)
            guard value.isFinite else {throw RopePhysicsError.invalid("Nonfinite rational portal Hessian")}
            matrix[i][j]=value;matrix[j][i]=value
        }}
        return matrix
    }
}
