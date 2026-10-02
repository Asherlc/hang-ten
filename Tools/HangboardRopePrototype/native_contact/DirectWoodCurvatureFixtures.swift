import Foundation
import simd

func check(_ value:Bool,_ reason:String) throws {if !value {throw RopePhysicsError.invalid(reason)}}
let vertexTriangle=[SIMD3<Double>(0,0,0),SIMD3<Double>(0,2,0),SIMD3<Double>(0,0,-2)]
do {
    let point=SIMD3<Double>(0.003,-0.004,0.002)
    let derivatives=[SIMD3<Double>(1,0,0),SIMD3<Double>(0,1,0),SIMD3<Double>(0,0,1),SIMD3<Double>(0,-1,0)]
    let result=try DirectWoodCurvature.selected(start:point,end:point,triangle:vertexTriangle,startDerivatives:derivatives,endDerivatives:derivatives)
    let distance=simd_length(point),normal=point/distance
    try check(abs(result.distance-distance)<1e-12,"Vertex distance differs")
    for i in derivatives.indices {for j in derivatives.indices {
        let expected=(simd_dot(derivatives[i],derivatives[j])-simd_dot(derivatives[i],normal)*simd_dot(derivatives[j],normal))/distance
        try check(abs(result.hessian[i][j]-expected)<1e-8,"Vertex/shared-height Hessian differs")
    }}
    print("PASS vertex distance and shared-height curvature")
    let face=[SIMD3<Double>(-2,-2,0),SIMD3<Double>(2,-2,0),SIMD3<Double>(0,2,0)]
    let planePoint=SIMD3<Double>(0,0,0.0036)
    let plane=try DirectWoodCurvature.selected(start:planePoint,end:planePoint,triangle:face,startDerivatives:derivatives,endDerivatives:derivatives)
    try check(plane.hessian.flatMap{$0}.allSatisfy{$0==0},"Interior plane has spurious curvature")
    print("PASS exact zero plane curvature")
    let edgePoint=SIMD3<Double>(0.003,1,0.004)
    let edge=try DirectWoodCurvature.selected(start:edgePoint,end:edgePoint,triangle:vertexTriangle,startDerivatives:derivatives,endDerivatives:derivatives)
    try check(abs(edge.distance-0.005)<1e-12 && abs(edge.hessian[0][0]-128)<1e-8 && abs(edge.hessian[2][2]-72)<1e-8 && abs(edge.hessian[1][1])<1e-8,"Edge curvature differs")
    print("PASS edge contact curvature")
    let interior=try DirectWoodCurvature.selected(start:SIMD3(-1,-1,1),end:SIMD3(1,-1,1),triangle:vertexTriangle,
        startDerivatives:[SIMD3(0,0,1),.zero],endDerivatives:[.zero,SIMD3(0,0,1)])
    let factor=1/(8*sqrt(2.0)),expected=[[-factor,3*factor],[3*factor,-factor]]
    for i in 0..<2 {for j in 0..<2 {try check(abs(interior.hessian[i][j]-expected[i][j])<1e-10,"Moving whole-link witness curvature differs")}}
    print("PASS interior whole-link witness fraction moves")
    let boundaryPoint=SIMD3<Double>(1,0,1)
    let boundary=try DirectWoodCurvature.selected(start:boundaryPoint,end:boundaryPoint,
        triangle:[SIMD3(0,0,0),SIMD3(2,0,0),SIMD3(0,2,0)],startDerivatives:derivatives,endDerivatives:derivatives)
    try check(boundary.tiedCandidates.isEmpty && !boundary.internalBoundaries.isEmpty,"Internal triangle boundary mistaken for a unique branch")
    print("PASS internal triangle boundary recorded without candidate tie")
    var rejected=false
    do {_ = try DirectWoodCurvature.selected(start:SIMD3(0,0,-1),end:SIMD3(0,0,1),triangle:face,startDerivatives:derivatives,endDerivatives:derivatives)}catch {rejected=true}
    try check(rejected,"Intersecting wood feature accepted")
    print("PASS intersecting derivative rejected")
}catch {print("FAIL",error);exit(1)}
