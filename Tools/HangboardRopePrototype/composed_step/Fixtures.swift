import Foundation
import simd

func composedFixtures(initial:RopeDynamicsSolver,input:RopePhysicsInput,collider:RopeTriangleCollider)throws {
    let h=RopeComposedStep.h,D=RopeComposedStep.damping,C=RopeComposedStep.velocityCoefficient
    let oldCoarse=4*h*h*(-9.81)*D*D
    let fineFree=h*h*(-9.81)*(2*D+D*D)
    guard abs(oldCoarse-fineFree)>0.0001 else {throw RopePhysicsError.invalid("old coarse gravity negative control did not fail")}
    var cases=0
    for v in [0.0,-0.2,0.2] {for g in [-9.81,0.0,9.81] {for a in [-30.0,0.0,30.0,-D*g] {
        let x=0.3,v1=D*(v+g*h)+h*a,x1=x+h*v1,v2=D*(v1+g*h)+h*a,x2=x1+h*v2
        let p1=D*(v+g*h),p2=D*(p1+g*h),predicted=(x+h*p1)+h*p2,delta=RopeComposedStep.responseSquare*a
        guard abs(predicted+delta-x2)<1e-14,abs(p2+C*delta/h-v2)<1e-13 else {
            throw RopePhysicsError.invalid("constant-force composition fixture")
        };cases+=1
    }}}
    let v=0.2,g = -9.81,a1=3.0,a2 = -4.0
    let p1=D*(v+g*h),p2=D*(p1+g*h)
    let fineV=D*(p1+h*a1+g*h)+h*a2
    let delta=h*h*((1+D)*a1+a2),coarseV=p2+C*delta/h
    guard abs((coarseV-fineV)-h*(a1-a2)/(2+D))<1e-13 else {throw RopePhysicsError.invalid("changing-force defect fixture")}
    guard abs(C*RopeComposedStep.arrivalLimit/h-0.001)<1e-15 else {throw RopePhysicsError.invalid("arrival speed scale fixture")}
    var checkpoint=initial.composedCheckpoint()
    checkpoint["composedResponseSquare"]=RopeComposedStep.responseSquare
    checkpoint["lastStepDuration"]=2*h
    checkpoint["distanceTension"]=initial.state.ropes.map{Array(repeating:2+D,count:$0.restLengths.count)}
    checkpoint["extraHints"]=[["indices":[0],"coefficients":[1.0],"border":[0.0],"residual":0.01,"lambda":2+D]]
    let restored=try RopeDynamicsSolver.restoreComposedReference(input:input,collider:collider,data:JSONSerialization.data(withJSONObject:checkpoint,options:[.sortedKeys]),strict:true)
    let values=restored.composedCheckpoint()
    guard (values["distanceTension"] as! [[Double]]).flatMap({$0}).allSatisfy({abs($0-1)<1e-14}),
          values["lastStepDuration"] as! Double==h else {throw RopePhysicsError.invalid("strict-reference tension conversion fixture")}
    var expected=checkpoint
    let factor=h*h/RopeComposedStep.responseSquare
    expected["distanceTension"]=(checkpoint["distanceTension"] as! [[Double]]).map{$0.map{$0*factor}}
    expected["extraHints"]=(checkpoint["extraHints"] as! [[String:Any]]).map {hint in
        var converted=hint;converted["lambda"]=(hint["lambda"] as! Double)*factor;return converted
    }
    expected["lastStepDuration"]=h
    expected["composedResponseSquare"]=h*h
    guard try JSONSerialization.data(withJSONObject:values,options:[.sortedKeys]) == JSONSerialization.data(withJSONObject:expected,options:[.sortedKeys]) else {
        throw RopePhysicsError.invalid("strict-reference changed another persisted field or missed contact hint conversion")
    }
    print("PASS composed fixtures",cases,"old gravity RED, constant-force GREEN, changing-force defect, arrival and reference scales")
}
