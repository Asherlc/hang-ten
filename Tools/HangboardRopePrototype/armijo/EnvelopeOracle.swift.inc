// Appended to the native solver's file; no product linkage.
extension RopeDynamicsSolver {
    private mutating func verifyArmijoSlope(before:RopeSimulationState,prediction:RopeSimulationState,weights:[[Double]],
        corrections:[[SIMD3<Double>]],height:Double,penalty:Double,score:Double,slope:Double) throws -> [[String:Double]] {
        let saved=cachedEvaluation
        defer {cachedEvaluation=saved}
        let evaluation=configurationEvaluation(before)
        var terms:[(arguments:[Double],rates:[Double])]=[]
        var relativeBound=0.0
        var objectiveSlope=before.boardMass*(before.boardHeight-prediction.boardHeight)*height
        var objectiveCurvature=before.boardMass*height*height
        for (r,rope) in before.ropes.enumerated() {
            let directions=rope.positions.indices.map{RopeArmijo.displacement(rope,$0,corrections[r][$0],height)}
            for i in rope.positions.indices {
                relativeBound=max(relativeBound,simd_length(directions[i]-SIMD3<Double>(0,height,0)))
                if weights[r][i]>0 {
                    objectiveSlope += simd_dot(rope.positions[i]-prediction.ropes[r].positions[i],directions[i])/weights[r][i]
                    objectiveCurvature += simd_length_squared(directions[i])/weights[r][i]
                }
            }
            for i in rope.restLengths.indices {
                let edge=rope.positions[i+1]-rope.positions[i],length=simd_length(edge)
                let residual=length-rope.restLengths[i],rate=simd_dot(edge/length,directions[i+1]-directions[i])
                terms.append(([residual,-residual],[rate,-rate]))
                let branches=evaluation.merits[r][i].flatMap{$0.armijoOracleBranches}
                let arguments=branches.map{$0.penetrationDepth-Self.contactLinearTolerance}
                let rates=branches.map {branch in
                    -simd_dot(before.orientation.act(branch.normal),
                        directions[i]*(1-branch.fraction)+directions[i+1]*branch.fraction-SIMD3<Double>(0,height,0))
                }
                terms.append((arguments,rates))
            }
            for (id,crossing) in rope.portalCrossings {
                let portal=portalMap[id]!,i=crossing.segment
                let boundaries=try RopePassageTopology.boundaryConstraints(from:before.boardPoint(rope.positions[i]),
                    to:before.boardPoint(rope.positions[i+1]),portal:portal,radius:rope.radius)
                let point=before.boardPoint(crossing.point(in:rope.positions))
                let arguments=portal.boundary.indices.map {j -> Double in
                    let start=portal.boundary[j],end=portal.boundary[(j+1)%portal.boundary.count]
                    var inward=simd_normalize(simd_cross(portal.normal,end-start))
                    if simd_dot(inward,portal.center-start)<0 {inward = -inward}
                    return rope.radius+RopeRegionGeometry.clearance-simd_dot(point-start,inward)-Self.contactLinearTolerance
                }
                let da=before.orientation.inverse.act(directions[i]-SIMD3<Double>(0,height,0))
                let db=before.orientation.inverse.act(directions[i+1]-SIMD3<Double>(0,height,0))
                let rates=boundaries.map{-simd_dot($0.firstGradient,da)-simd_dot($0.secondGradient,db)}
                terms.append((arguments,rates))
            }
        }
        let independentSlope=objectiveSlope+penalty*terms.reduce(0.0){sum,term in
            guard let maximum=term.arguments.max() else {return sum}
            let rate=term.rates.indices.filter{term.arguments[$0]==maximum}.map{term.rates[$0]}.max()!
            return sum+RopeArmijo.hingeSlope(argument:maximum,rate:rate)
        }
        let parityError=abs(independentSlope-slope)
        var checks:[[String:Double]]=[]
        for h in [1e-3,1e-4,1e-5,1e-6,1e-7] {
            var trial=before;trial.boardHeight += height*h
            for r in trial.ropes.indices {
                for i in trial.ropes[r].positions.indices {trial.ropes[r].positions[i] += corrections[r][i]*h}
                for (i,local) in trial.ropes[r].attachments {trial.ropes[r].positions[i]=trial.worldPoint(local)}
            }
            var supported=true
            do {try RopePassageTopology.refresh(state:&trial,input:input)} catch RopePhysicsError.invalid {supported=false}
            for r in before.ropes.indices {for (id,crossing) in before.ropes[r].portalCrossings {
                if trial.ropes[r].portalCrossings[id]?.segment != crossing.segment {supported=false}
            }}
            let numerical=(try merit(trial,prediction:prediction,weights:weights,penalty:penalty)-score)/h
            let predicted=objectiveSlope+0.5*h*objectiveCurvature+penalty*terms.reduce(0.0){sum,term in
                sum+(RopeArmijo.envelopeModel(arguments:term.arguments,rates:term.rates,alpha:h) -
                    RopeArmijo.envelopeModel(arguments:term.arguments,rates:term.rates,alpha:0))/h
            }
            checks.append(["alpha":h,"analytic":slope,"independentSlope":independentSlope,
                "slopeParityError":parityError,"numerical":numerical,"predictedSecant":predicted,
                "rawDerivativeError":abs(numerical-slope),"error":abs(numerical-predicted),
                "portalBranchSupported":supported ? 1:0,"relativePerturbation":h*relativeBound])
        }
        let last=checks.last!
        guard parityError<=1e-8,last["error"]!<=1e-8,last["portalBranchSupported"]! == 1,
            last["relativePerturbation"]!<Self.contactLinearTolerance else {
            ArmijoTrace.derivativeFailures.append(["checks":checks,"before":bundleCheckpoint(),
                "corrections":corrections.map{$0.map{[$0.x,$0.y,$0.z]}},"height":height,"penalty":penalty,"score":score])
            throw RopePhysicsError.invalid("branch-envelope merit oracle")
        }
        return checks
    }
}
