import simd
func ambiguityFixtures()throws {
    let previous=ArmijoTrace.collectDerivatives
    ArmijoTrace.collectDerivatives=true
    defer {ArmijoTrace.collectDerivatives=previous}
    let a=SIMD3<Double>(-0.01,-0.01,-0.01),b=SIMD3<Double>(0.01,0,0.01)
    let v=[SIMD3(a.x,a.y,a.z),SIMD3(b.x,a.y,a.z),SIMD3(b.x,b.y,a.z),SIMD3(a.x,b.y,a.z),
        SIMD3(a.x,a.y,b.z),SIMD3(b.x,a.y,b.z),SIMD3(b.x,b.y,b.z),SIMD3(a.x,b.y,b.z)]
    let triangles=[SIMD3(0,2,1),SIMD3(0,3,2),SIMD3(4,5,6),SIMD3(4,6,7),SIMD3(0,1,5),SIMD3(0,5,4),
        SIMD3(1,2,6),SIMD3(1,6,5),SIMD3(2,3,7),SIMD3(2,7,6),SIMD3(3,0,4),SIMD3(3,4,7)]
    let collider=try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:v,triangles:triangles))
    let p=SIMD3<Double>(-0.004,0.00355,0.005),q=SIMD3<Double>(-0.002,0.00355,0.005)
    let parallel=collider.fusedContactEvaluation(from:p,to:q,rowRadius:0.00365,meritRadius:0.0036,
        startInside:false,endInside:false).hits[2]
    guard !parallel.isEmpty,parallel.filter{$0.penetrationDepth==parallel.map{$0.penetrationDepth}.max()!}.allSatisfy({!$0.armijoWitnessUnique}) else {
        throw RopePhysicsError.invalid("parallel face tied minimizers not marked ambiguous")
    }
    let maximum=parallel.map{$0.penetrationDepth}.max()!
    let witnesses=parallel.filter{$0.penetrationDepth==maximum}.flatMap{$0.armijoDerivativeWitnesses}
    guard witnesses.contains(where:{$0.fraction==0}),witnesses.contains(where:{$0.fraction==1}) else {
        throw RopePhysicsError.invalid("tied start/end derivative witnesses missing")
    }
    let da=SIMD3<Double>(0,1,0),db=SIMD3<Double>(0,-1,0),h=1e-7
    let predicted=witnesses.map{-simd_dot($0.normal,da*(1-$0.fraction)+db*$0.fraction)}.max()!
    let perturbed=collider.fusedContactEvaluation(from:p+da*h,to:q+db*h,rowRadius:0.00365,meritRadius:0.0036,
        startInside:false,endInside:false).hits[2].map{$0.penetrationDepth}.max()!
    guard abs(predicted-(perturbed-maximum)/h)<1e-8 else {
        throw RopePhysicsError.invalid("parallel-link one-sided derivative disagrees")
    }
    let point=collider.fusedContactEvaluation(from:p,to:p,rowRadius:0.00365,meritRadius:0.0036,
        startInside:false,endInside:false).hits[2]
    guard !point.isEmpty,point.filter{$0.penetrationDepth==point.map{$0.penetrationDepth}.max()!}.allSatisfy({$0.armijoWitnessUnique}) else {
        throw RopePhysicsError.invalid("unique point witness marked ambiguous")
    }
}
