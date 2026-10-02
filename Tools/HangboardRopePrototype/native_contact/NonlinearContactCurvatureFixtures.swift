import Foundation
import simd

func check(_ condition:Bool,_ reason:String) throws {if !condition {throw RopePhysicsError.invalid(reason)}}
do {
    let coordinates=[0.003,0.004,0.0,0.0]
    let actual=try NonlinearContactCurvature.hessian(count:4,minimumRest:0.002) {axis,change in
        var x=coordinates;x[axis] += change
        let p=SIMD3(x[0],x[1]-x[3],x[2]),n=p/simd_length(p)
        return [n.x,n.y,n.z,-n.y]
    }
    let expected=[[128.0,-96,0,96],[-96,72,0,-72],[0,0,200,0],[96,-72,0,72]]
    for r in 0..<4 {for c in 0..<4 {try check(abs(actual.matrix[r][c]-expected[r][c])<1e-4,"Curved vertex/shared-height Hessian differs")}}
    try check(actual.asymmetry<1e-4,"Unexpected smooth curvature asymmetry")
    print("PASS vertex contact and shared board-height curvature")
    let plane=try NonlinearContactCurvature.hessian(count:4,minimumRest:0.002) {_,_ in [0,1,0,-1]}
    try check(plane.matrix.flatMap{$0}.allSatisfy{$0==0},"Plane has invented curvature")
    print("PASS interior plane has zero contact curvature")
    var rejected=false
    do {_ = try NonlinearContactCurvature.hessian(count:0,minimumRest:0.002) {_,_ in []}}catch {rejected=true}
    try check(rejected,"Invalid stencil accepted")
    print("PASS invalid contact-curvature input rejected")
} catch {print("FAIL",error);exit(1)}
