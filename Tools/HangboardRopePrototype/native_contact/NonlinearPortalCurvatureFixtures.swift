import Foundation
import simd

func check(_ condition:Bool,_ reason:String) throws {if !condition {throw RopePhysicsError.invalid(reason)}}
do {
    let a=SIMD3<Double>(2,0,-1),b=SIMD3<Double>(4,0,1),normal=SIMD3<Double>(0,0,1),inward=SIMD3<Double>(1,0,0)
    let da=[SIMD3<Double>(1,0,0),SIMD3<Double>(0,0,1),SIMD3<Double>(0,0,-1)]
    let db=[SIMD3<Double>.zero,.zero,SIMD3<Double>(0,0,-1)]
    let h=try NonlinearPortalCurvature.hessian(a:a,b:b,center:.zero,normal:normal,inward:inward,da:da,db:db)
    let expected=[[0.0,0.25,-0.5],[0.25,-0.5,0.5],[-0.5,0.5,0.0]]
    for i in 0..<3 {for j in 0..<3 {try check(abs(h[i][j]-expected[i][j])<1e-12,"Rational portal/shared-height Hessian differs")}}
    print("PASS direct rational portal and shared-height Hessian")
    let near=try NonlinearPortalCurvature.hessian(a:SIMD3(2,0,-1e-12),b:b,center:.zero,normal:normal,inward:inward,da:da,db:db)
    try check(near.flatMap{$0}.allSatisfy{$0.isFinite},"Near-endpoint derivative is invalid")
    print("PASS valid near-endpoint crossing without a perturbed physical state")
    for invalid in [SIMD3<Double>(2,0,2),SIMD3<Double>(2,0,1)] {
        var rejected=false
        do {_ = try NonlinearPortalCurvature.hessian(a:invalid,b:b,center:.zero,normal:normal,inward:inward,da:da,db:db)}catch {rejected=true}
        try check(rejected,"Invalid portal derivative accepted")
    }
    print("PASS out-of-segment and tangent portal Hessians rejected")
} catch {print("FAIL",error);exit(1)}
