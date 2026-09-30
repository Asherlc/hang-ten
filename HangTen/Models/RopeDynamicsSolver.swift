import simd

/// Inextensible chain with a coupled mass-metric nonlinear projection. The scalar
/// board-height degree of freedom participates in the same solve as the rope.
struct RopeDynamicsSolver: Sendable {
    let input:RopePhysicsInput
    let collider:RopeTriangleCollider
    private(set) var state:RopeSimulationState
    private var time=0.0
    private var history:[(Double,Double)]=[]
    private var acceptedMinimumClearance:Double?
    private let portalMap:[String:RopePortalRegion]
    private var distanceTension:[[Double]]
    private var lastStepDuration=1.0/240

    init(input:RopePhysicsInput,state:RopeSimulationState,collider:RopeTriangleCollider) throws {
        self.input=input;self.state=state;self.collider=collider
        portalMap=Dictionary(uniqueKeysWithValues:input.portals.map{($0.id,$0)})
        guard let profile=input.profiles.first(where:{$0.id == state.profileID}),
              profile.ropes.count == state.ropes.count,state.boardMass == profile.boardMass,
              zip(profile.ropes,state.ropes).allSatisfy({source,chain in
                  source.id == chain.id && source.radius == chain.radius && source.linearMass == chain.linearMass &&
                  abs(source.restLength-chain.restLengths.reduce(0,+))<1e-8
              }),Self.finite(state.orientation.vector.xyz),state.orientation.vector.w.isFinite,
              abs(simd_length(state.orientation.vector)-1)<1e-8,
              state.boardMass>0,state.boardMass.isFinite,state.boardHeight.isFinite,
              state.boardVerticalVelocity.isFinite,!state.ropes.isEmpty,
              state.ropes.allSatisfy({rope in
                  rope.positions.count == rope.restLengths.count+1 && rope.positions.count == rope.velocities.count &&
                  rope.positions.count == rope.previousPositions.count && rope.radius>0 && rope.linearMass>0 &&
                  rope.positions.allSatisfy(Self.finite) && rope.previousPositions.allSatisfy(Self.finite) &&
                  rope.velocities.allSatisfy(Self.finite) &&
                  rope.restLengths.allSatisfy{$0.isFinite && $0>0} &&
                  rope.supports.keys.allSatisfy{rope.positions.indices.contains($0)} &&
                  rope.portals.keys.allSatisfy{rope.positions.indices.contains($0)}
              }) else{throw RopePhysicsError.invalid("Invalid or nonfinite simulation state")}
        history=[(0,state.boardHeight)]
        distanceTension=state.ropes.map{Array(repeating:0,count:$0.restLengths.count)}
    }

    mutating func step(dt:Double,targetOrientation:simd_quatd) throws -> RopeFrameSnapshot {
        var candidate=self
        let frame=try candidate.advanceBounded(dt:dt,targetOrientation:targetOrientation,depth:0)
        self=candidate
        return frame
    }

    private enum StepFailure:Error {case sweptWoodTraversal,sweptSelfTraversal,nonlinearConvergence,geometry(RopeSimulationMetrics)}

    private mutating func advanceBounded(dt:Double,targetOrientation:simd_quatd,depth:Int) throws -> RopeFrameSnapshot {
        var trial=self
        do {
            let frame=try trial.advance(dt:dt,targetOrientation:targetOrientation)
            self=trial;return frame
        } catch let failure as StepFailure {
            guard depth<4 else {
                if case .geometry(let metrics)=failure {
                    throw RopePhysicsError.invalid("Bounded solve failed: strain \(metrics.maximumLocalStrain), length \(metrics.totalLengthError), clearance margin \(metrics.minimumClearanceMargin), topology \(metrics.topologyFailure ?? "valid")")
                }
                throw RopePhysicsError.invalid("Bounded solve could not resolve \(failure)")
            }
            trial=self
            _ = try trial.advanceBounded(dt:dt/2,targetOrientation:targetOrientation,depth:depth+1)
            let frame=try trial.advanceBounded(dt:dt/2,targetOrientation:targetOrientation,depth:depth+1)
            self=trial;return frame
        }
    }

    private mutating func advance(dt:Double,targetOrientation:simd_quatd) throws -> RopeFrameSnapshot {
        guard dt.isFinite,dt>0,dt<=1.0/120,Self.finite(targetOrientation.vector.xyz),targetOrientation.vector.w.isFinite,
              abs(simd_length(targetOrientation.vector)-1)<1e-8 else {
            throw RopePhysicsError.invalid("Invalid fixed step or target orientation")
        }
        let old=state
        let tensionScale=pow(dt/lastStepDuration,2)
        distanceTension=distanceTension.map{$0.map{$0*tensionScale}}
        let dot=min(1,abs(simd_dot(old.orientation.vector,targetOrientation.vector)))
        let angle=2*acos(dot),fraction=angle>1e-9 ? min(1,dt*2.1/angle):1
        state.orientation=simd_slerp(old.orientation,targetOrientation,fraction)
        let damping=exp(-18*dt)
        state.boardVerticalVelocity=(old.boardVerticalVelocity-9.81*dt)*damping
        state.boardHeight += state.boardVerticalVelocity*dt
        for r in state.ropes.indices {
            let rope=old.ropes[r]
            for i in rope.positions.indices {
                if let support=rope.supports[i] {state.ropes[r].positions[i]=support;continue}
                if let attachment=rope.attachments[i] {
                    state.ropes[r].positions[i]=state.worldPoint(attachment)
                } else {
                    state.ropes[r].positions[i] += (rope.velocities[i]+SIMD3(0,-9.81*dt,0))*damping*dt
                }
            }
        }
        let prediction=state
        try RopePassageTopology.refresh(state:&state,input:input)
        for _ in 0..<80 {
            let movement=try correctConstraints(prediction:prediction)
            if maximumStrain()<0.0002 && movement<1e-8 {break}
        }
        for r in state.ropes.indices {
            let radius=state.ropes[r].radius-0.00005
            let rotationAngle=2*acos(min(1,abs(simd_dot(old.orientation.vector,state.orientation.vector))))
            func deviation(_ i:Int)->Double {
                if state.ropes[r].attachments[i] != nil {return 0}
                return RopeMotionSweep.rotationalDeviation(
                    start:old.ropes[r].positions[i]-SIMD3(0,old.boardHeight,0),
                    end:state.ropes[r].positions[i]-SIMD3(0,state.boardHeight,0),angle:rotationAngle)
            }
            for i in state.ropes[r].restLengths.indices {
                let a=old.boardPoint(old.ropes[r].positions[i]),b=old.boardPoint(old.ropes[r].positions[i+1])
                let nextA=state.boardPoint(state.ropes[r].positions[i]),nextB=state.boardPoint(state.ropes[r].positions[i+1])
                let movement=max(simd_distance(a,nextA),simd_distance(b,nextB))
                let curveDeviation=max(deviation(i),deviation(i+1))
                let oldClearance=acceptedMinimumClearance ?? collider.segmentClearance(from:a,to:b)
                // Signed distance is 1-Lipschitz. This bound certifies the
                // complete segment motion; uncertain moves use exact CCD.
                if movement+curveDeviation<=oldClearance-radius {continue}
                if collider.sweptSegmentContact(previousStart:a,previousEnd:b,start:nextA,end:nextB,radius:radius+curveDeviation) != nil {
                    throw StepFailure.sweptWoodTraversal
                }
            }
            guard RopeMotionSweep.selfContactValid(previous:old.ropes[r].positions,positions:state.ropes[r].positions,
                radius:state.ropes[r].radius,supports:state.ropes[r].supports,restLengths:state.ropes[r].restLengths) else {
                throw StepFailure.sweptSelfTraversal
            }
        }
        for r in state.ropes.indices {
            state.ropes[r].previousPositions=old.ropes[r].positions
            for i in state.ropes[r].positions.indices {
                state.ropes[r].velocities[i]=(state.ropes[r].positions[i]-old.ropes[r].positions[i])/dt
            }
        }
        state.boardVerticalVelocity=(state.boardHeight-old.boardHeight)/dt
        guard state.boardHeight.isFinite,state.ropes.allSatisfy({$0.positions.allSatisfy(Self.finite)}) else {
            state=old;throw RopePhysicsError.invalid("Dynamics produced nonfinite state")
        }
        time += dt;history.append((time,state.boardHeight))
        history.removeAll{$0.0<time-0.5-dt/2}
        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1})
        guard metrics.geometryAccepted else {
            state=old;throw StepFailure.geometry(metrics)
        }
        acceptedMinimumClearance=metrics.minimumSegmentClearance
        lastStepDuration=dt
        let arrived=abs(simd_dot(state.orientation.vector,targetOrientation.vector))>1-1e-12
        let settled=arrived && time>=0.5 && metrics.maximumSpeed<0.001 && metrics.boardDisplacement<0.0001
        return RopeFrameSnapshot(boardHeight:state.boardHeight,orientation:state.orientation,
            ropes:state.ropes.map{RopeChainSnapshot(id:$0.id,radius:$0.radius,positions:$0.positions)},settled:settled,metrics:metrics)
    }

    mutating func settled(targetOrientation:simd_quatd,maxDuration:Double) throws -> RopeFrameSnapshot {
        guard maxDuration.isFinite,maxDuration>0 else{throw RopePhysicsError.invalid("Invalid settling duration")}
        for _ in 0..<Int(ceil(maxDuration*240)) {
            let frame=try step(dt:1.0/240,targetOrientation:targetOrientation)
            if frame.settled {return frame}
        }
        throw RopePhysicsError.invalid("Rope did not converge within \(maxDuration) seconds")
    }

    private static func finite(_ point:SIMD3<Double>)->Bool {point.x.isFinite && point.y.isFinite && point.z.isFinite}

    private func maximumStrain()->Double {
        state.ropes.reduce(0) {value,rope in
            max(value,rope.restLengths.indices.reduce(0){max($0,abs(simd_distance(rope.positions[$1],rope.positions[$1+1])/rope.restLengths[$1]-1))})
        }
    }

    private struct ConstraintRow {
        let rope:Int
        let particles:[Int]
        let gradients:[SIMD3<Double>]
        let boardGradient:Double
        let residual:Double
        let contact:Bool
        let lengthSegment:Int?
    }

    /// Distance and exact capsule contact share a sparse coupled solve.
    /// CAD wood constrains the aperture; crossings identify topology without
    /// pinning material. Unilateral tensile contacts are released, with inactive
    /// inequalities reconsidered before accepting a correction.
    private mutating func correctConstraints(prediction:RopeSimulationState) throws -> Double {
        var rows:[ConstraintRow]=[]
        var weights:[[Double]]=[]
        let worldUp=SIMD3<Double>(0,1,0)
        for (r,rope) in state.ropes.enumerated() {
            let links=rope.restLengths.count
            weights.append(rope.positions.indices.map {i in
                if rope.supports[i] != nil || rope.attachments[i] != nil {return 0}
                let length=(i>0 ? rope.restLengths[i-1]:0)+(i<links ? rope.restLengths[i]:0)
                return 2/(rope.linearMass*length)
            })
            for i in rope.positions.indices {
                for hit in collider.segmentContacts(from:state.boardPoint(rope.positions[i]),to:state.boardPoint(rope.positions[i]),
                    radius:rope.radius+RopeRegionGeometry.clearance+0.00005) {
                    let normal=state.orientation.act(hit.normal)
                    let attached=rope.attachments[i] == nil ? SIMD3<Double>.zero:worldUp
                    rows.append(ConstraintRow(rope:r,particles:[i],gradients:[normal],
                        boardGradient:-normal.y+simd_dot(normal,attached),residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))
                }
                guard i<links else{continue}
                let delta=rope.positions[i+1]-rope.positions[i],length=simd_length(delta)
                guard length>1e-12 else{throw RopePhysicsError.invalid("Collapsed rope link")}
                let tangent=delta/length
                let attachedA=rope.attachments[i] == nil ? SIMD3<Double>.zero:worldUp
                let attachedB=rope.attachments[i+1] == nil ? SIMD3<Double>.zero:worldUp
                rows.append(ConstraintRow(rope:r,particles:[i,i+1],gradients:[-tangent,tangent],
                    boardGradient:simd_dot(tangent,attachedB-attachedA),residual:length-rope.restLengths[i],contact:false,lengthSegment:i))
                let a=state.boardPoint(rope.positions[i]),b=state.boardPoint(rope.positions[i+1])
                for hit in collider.segmentContacts(from:a,to:b,radius:rope.radius+RopeRegionGeometry.clearance+0.00005) where hit.fraction>1e-6 && hit.fraction<1-1e-6 {
                    let normal=state.orientation.act(hit.normal),f=hit.fraction
                    let gradients=[normal*(1-f),normal*f]
                    let boardGradient = -normal.y+simd_dot(gradients[0],attachedA)+simd_dot(gradients[1],attachedB)
                    rows.append(ConstraintRow(rope:r,particles:[i,i+1],gradients:gradients,boardGradient:boardGradient,
                        residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))
                }
            }
            if let pair=RopeSimulationMetrics.selfContactPair(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths) {
                let i=pair.x,j=pair.y
                let witness=RopeTriangleCollider.segmentPair(rope.positions[i],rope.positions[i+1],rope.positions[j],rope.positions[j+1])
                let delta=witness.0-witness.1,distance=simd_length(delta),f=witness.2
                let edge=rope.positions[j+1]-rope.positions[j]
                let g=min(1,max(0,simd_dot(witness.1-rope.positions[j],edge)/simd_length_squared(edge)))
                var normal=distance>1e-10 ? delta/distance:simd_cross(rope.positions[i+1]-rope.positions[i],edge)
                normal=simd_length(normal)>1e-10 ? simd_normalize(normal):SIMD3(1,0,0)
                let indices=[i,i+1,j,j+1],gradients=[normal*(1-f),normal*f,-normal*(1-g),-normal*g]
                let boardGradient=zip(indices,gradients).reduce(0.0){value,item in
                    value+(rope.attachments[item.0] == nil ? 0:item.1.y)
                }
                rows.append(ConstraintRow(rope:r,particles:indices,gradients:gradients,boardGradient:boardGradient,
                    residual:distance-2*rope.radius-0.00005,contact:true,lengthSegment:nil))
            }
        }
        // Separated candidate facets are inequalities, not initial equalities.
        // Starting them active needlessly factors/releases hundreds of rows.
        // The loop below still inserts any inactive inequality a solve violates.
        var activeIDs=rows.indices.filter{!rows[$0].contact || rows[$0].residual<=1e-9}
        var selected=activeIDs.map{rows[$0]}
        for _ in 0..<(rows.count*2+10) {
            let solved=try coupledCorrection(rows:selected,weights:weights,prediction:prediction)
            let lambda=solved.multipliers,heightCorrection=solved.height,corrections=solved.particles
            if let released=selected.indices.filter({selected[$0].contact && lambda[$0]>1e-12}).max(by:{lambda[$0]<lambda[$1]}) {
                activeIDs.remove(at:released)
                selected=activeIDs.map{rows[$0]}
                continue
            }
            let active=Set(activeIDs)
            var worst:(Int,Double)?
            for index in rows.indices where rows[index].contact && !active.contains(index) {
                let row=rows[index]
                var residual=row.residual+row.boardGradient*heightCorrection
                for j in row.particles.indices {residual += simd_dot(row.gradients[j],corrections[row.rope][row.particles[j]])}
                if residual < -1e-8 && residual < (worst?.1 ?? 0) {worst=(index,residual)}
            }
            if let index=worst?.0 {
                activeIDs.append(index);activeIDs.sort();selected=activeIDs.map{rows[$0]};continue
            }
            let before=state
            let maximum=corrections.flatMap{$0}.map{simd_length($0)}.max() ?? 0
            let shortest=state.ropes.flatMap{$0.restLengths}.min()!
            var alpha=min(1,0.1*shortest/max(1e-12,max(maximum,abs(heightCorrection))))
            let penalty=max(1,2*(lambda.map{abs($0)}.max() ?? 0))
            let score=try merit(state,prediction:prediction,weights:weights,penalty:penalty)
            for _ in 0..<16 {
                state=before
                state.boardHeight += heightCorrection*alpha
                for r in state.ropes.indices {
                    for i in state.ropes[r].positions.indices {state.ropes[r].positions[i] += corrections[r][i]*alpha}
                    for (index,local) in state.ropes[r].attachments {state.ropes[r].positions[index]=state.worldPoint(local)}
                }
                do {
                    try RopePassageTopology.refresh(state:&state,input:input)
                    if try merit(state,prediction:prediction,weights:weights,penalty:penalty)<=score+1e-18 {
                        for (index,row) in selected.enumerated() {
                            if let link=row.lengthSegment {
                                let old=distanceTension[row.rope][link]
                                distanceTension[row.rope][link]=max(0,(1-alpha)*old+alpha*lambda[index])
                            }
                        }
                        return alpha*max(maximum,abs(heightCorrection))
                    }
                } catch RopePhysicsError.invalid { }
                alpha *= 0.5
            }
            state=before
            throw StepFailure.nonlinearConvergence
        }
        throw StepFailure.nonlinearConvergence
    }

    /// Primal KKT system: particle inertia plus tension curvature, local
    /// length/contact rows, and borders for height/nonlocal self-contact.
    private func coupledCorrection(rows:[ConstraintRow],weights:[[Double]],prediction:RopeSimulationState) throws
        -> (particles:[[SIMD3<Double>]],height:Double,multipliers:[Double]) {
        let borderRows=rows.indices.filter{rows[$0].particles.max()!-rows[$0].particles.min()!>1}
        let borderSet=Set(borderRows),local=rows.indices.filter{!borderSet.contains($0)}
        var grouped:[SIMD2<Int>:[Int]]=[:]
        for index in local {
            let row=rows[index],key=SIMD2(row.rope,row.particles.min()!)
            grouped[key,default:[]].append(index)
        }
        var variables=state.ropes.map{Array(repeating:SIMD3<Int>(repeating:-1),count:$0.positions.count)}
        var rowVariables:[Int:Int]=[:],size=0
        for r in state.ropes.indices {
            for i in state.ropes[r].positions.indices {
                if weights[r][i]>0 {variables[r][i]=SIMD3(size,size+1,size+2);size += 3}
                for row in grouped[SIMD2(r,i)] ?? [] {rowVariables[row]=size;size += 1}
            }
        }
        var bandwidth=0
        for index in local {
            let row=rows[index],variable=rowVariables[index]!
            for particle in row.particles {
                for axis in 0..<3 where variables[row.rope][particle][axis]>=0 {
                    bandwidth=max(bandwidth,abs(variable-variables[row.rope][particle][axis]))
                }
            }
        }
        for r in state.ropes.indices {
            for i in state.ropes[r].positions.indices where weights[r][i]>0 {
                bandwidth=max(bandwidth,2)
                if i+1<state.ropes[r].positions.count,weights[r][i+1]>0 {
                    bandwidth=max(bandwidth,variables[r][i+1].z-variables[r][i].x)
                }
            }
        }
        var system=try RopeBandedSystem(size:size,bandwidth:bandwidth)
        let borderCount=1+borderRows.count
        var columns=Array(repeating:Array(repeating:0.0,count:size),count:borderCount)
        var border=Array(repeating:Array(repeating:0.0,count:borderCount),count:borderCount)
        var rhs=Array(repeating:0.0,count:size),borderRHS=Array(repeating:0.0,count:borderCount)
        border[0][0]=state.boardMass
        borderRHS[0] = -state.boardMass*(state.boardHeight-prediction.boardHeight)
        for r in state.ropes.indices {
            let rope=state.ropes[r]
            for i in rope.positions.indices where weights[r][i]>0 {
                let mass=1/weights[r][i],offset=rope.positions[i]-prediction.ropes[r].positions[i]
                for axis in 0..<3 {
                    let variable=variables[r][i][axis]
                    try system.addSymmetric(row:variable,column:variable,value:mass)
                    rhs[variable] = -mass*offset[axis]
                }
            }
            for i in rope.restLengths.indices {
                let delta=rope.positions[i+1]-rope.positions[i],length=simd_length(delta),tangent=delta/length
                let stiffness=max(0,distanceTension[r][i])/length
                guard stiffness>0 else{continue}
                func coefficient(_ a:Int,_ b:Int)->Double {stiffness*((a == b ? 1.0:0)-tangent[a]*tangent[b])}
                for particle in [i,i+1] where weights[r][particle]>0 {
                    for a in 0..<3 {for b in 0...a {
                        try system.addSymmetric(row:variables[r][particle][a],column:variables[r][particle][b],value:coefficient(a,b))
                    }}
                }
                if weights[r][i]>0,weights[r][i+1]>0 {
                    for a in 0..<3 {for b in 0..<3 {
                        try system.addSymmetric(row:variables[r][i][a],column:variables[r][i+1][b],value:-coefficient(a,b))
                    }}
                }
                let attachedDifference=(rope.attachments[i+1] == nil ? 0.0:1)-(rope.attachments[i] == nil ? 0.0:1)
                if attachedDifference != 0 {
                    border[0][0] += coefficient(1,1)*attachedDifference*attachedDifference
                    for (particle,sign) in [(i,-1.0),(i+1,1.0)] where weights[r][particle]>0 {
                        for axis in 0..<3 {columns[0][variables[r][particle][axis]] += sign*coefficient(axis,1)*attachedDifference}
                    }
                }
            }
        }
        for index in local {
            let row=rows[index],variable=rowVariables[index]!
            rhs[variable] = -row.residual
            // Numerical rank regularization, not authored rope elasticity;
            // acceptance still measures actual immutable length and clearance.
            try system.addSymmetric(row:variable,column:variable,value:-1e-8)
            columns[0][variable]=row.boardGradient
            for j in row.particles.indices {
                for axis in 0..<3 where variables[row.rope][row.particles[j]][axis]>=0 {
                    try system.addSymmetric(row:variable,column:variables[row.rope][row.particles[j]][axis],value:row.gradients[j][axis])
                }
            }
        }
        for (offset,index) in borderRows.enumerated() {
            let row=rows[index],variable=offset+1
            border[variable][variable] = -1e-8
            border[0][variable]=row.boardGradient;border[variable][0]=row.boardGradient
            borderRHS[variable] = -row.residual
            for j in row.particles.indices {
                for axis in 0..<3 where variables[row.rope][row.particles[j]][axis]>=0 {
                    columns[variable][variables[row.rope][row.particles[j]][axis]] += row.gradients[j][axis]
                }
            }
        }
        let solved=try system.solve(rhs:rhs,borderColumns:columns,borderMatrix:border,borderRHS:borderRHS)
        var corrections=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
        for r in state.ropes.indices {
            for i in state.ropes[r].positions.indices where weights[r][i]>0 {
                let v=variables[r][i]
                corrections[r][i]=SIMD3(solved.base[v.x],solved.base[v.y],solved.base[v.z])
            }
        }
        var multipliers=Array(repeating:0.0,count:rows.count)
        for index in local {multipliers[index]=solved.base[rowVariables[index]!]}
        for (offset,index) in borderRows.enumerated() {multipliers[index]=solved.border[offset+1]}
        return (corrections,solved.border[0],multipliers)
    }

    private func merit(_ candidate:RopeSimulationState,prediction:RopeSimulationState,weights:[[Double]],penalty:Double) throws -> Double {
        var objective=0.5*state.boardMass*pow(candidate.boardHeight-prediction.boardHeight,2),violation=0.0
        for (r,rope) in candidate.ropes.enumerated() {
            for i in rope.positions.indices where weights[r][i]>0 {
                objective += 0.5*simd_length_squared(rope.positions[i]-prediction.ropes[r].positions[i])/weights[r][i]
            }
            for i in rope.restLengths.indices {
                violation += abs(simd_distance(rope.positions[i],rope.positions[i+1])-rope.restLengths[i])
                let hits=collider.segmentContacts(from:candidate.boardPoint(rope.positions[i]),to:candidate.boardPoint(rope.positions[i+1]),
                    radius:rope.radius+RopeRegionGeometry.clearance)
                violation += hits.map{$0.penetrationDepth}.max() ?? 0
            }
            if let pair=RopeSimulationMetrics.selfContactPair(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths) {
                let points=RopeTriangleCollider.segmentPair(rope.positions[pair.x],rope.positions[pair.x+1],rope.positions[pair.y],rope.positions[pair.y+1])
                violation += max(0,2*rope.radius+0.00005-simd_distance(points.0,points.1))
            }
            for (id,crossing) in rope.portalCrossings {
                guard let portal=portalMap[id] else{throw RopePhysicsError.invalid("Missing merit portal")}
                let margin=RopePassageTopology.boundaryMargin(candidate.boardPoint(crossing.point(in:rope.positions)),portal:portal)
                violation += max(0,rope.radius+RopeRegionGeometry.clearance-margin)
            }
        }
        return objective+penalty*violation
    }

}

enum RopeMotionSweep {
    /// Under slerp, |p''(t)| <= angle² max|r(t)| + 2 angle |r'(t)|
    /// for p(t)=q(t)^-1 r(t). Linear-interpolation error is at most |p''|/8.
    /// Inflate the chord sweep by this bound to cover the true rotating path.
    static func rotationalDeviation(start:SIMD3<Double>,end:SIMD3<Double>,angle:Double)->Double {
        (angle*angle*max(simd_length(start),simd_length(end))+2*angle*simd_distance(start,end))/8
    }

    /// Conservative advancement between moving material segments. Connected
    /// bend capsules may overlap, but their centerlines cannot cross. Only the
    /// common knot endpoint is trimmed; the mouths/free spans remain checked.
    static func selfContactValid(previous:[SIMD3<Double>],positions:[SIMD3<Double>],radius:Double,
                                 supports:[Int:SIMD3<Double>],restLengths:[Double])->Bool {
        let links=restLengths.count
        var arc=[0.0]
        for length in restLengths {arc.append(arc.last!+length)}
        let common=supports[0].flatMap{a in supports[links].flatMap{b in simd_distance(a,b)<1e-10 ? a:nil}}
        for i in 0..<links {
            guard i+2<links else{continue}
            for j in (i+2)..<links {
                let connected=arc[j]-arc[i+1]<Double.pi*radius
                let knot=common != nil && min(arc[i],arc.last!-arc[i+1])<4*radius && min(arc[j],arc.last!-arc[j+1])<4*radius
                let distanceThreshold=connected || knot ? 1e-8:2*radius-0.00005
                var a=previous[i],b=previous[i+1],c=previous[j],d=previous[j+1]
                var nextA=positions[i],nextB=positions[i+1],nextC=positions[j],nextD=positions[j+1]
                if knot {
                    if i == 0 {
                        let f=min(1,1e-6/restLengths[i])
                        a += (b-a)*f;nextA += (nextB-nextA)*f
                    }
                    if j == links-1 {
                        let f=min(1,1e-6/restLengths[j])
                        d += (c-d)*f;nextD += (nextC-nextD)*f
                    }
                }
                let low=simd_min(simd_min(a,b),simd_min(nextA,nextB)),high=simd_max(simd_max(a,b),simd_max(nextA,nextB))
                let otherLow=simd_min(simd_min(c,d),simd_min(nextC,nextD)),otherHigh=simd_max(simd_max(c,d),simd_max(nextC,nextD))
                let separation=simd_max(simd_max(low-otherHigh,otherLow-high),SIMD3(repeating:0))
                if simd_length_squared(separation)>=distanceThreshold*distanceThreshold {continue}
                let motion=max(simd_distance(a,nextA),simd_distance(b,nextB))+max(simd_distance(c,nextC),simd_distance(d,nextD))
                var t=0.0,certified=false
                for _ in 0..<256 {
                    let pair=RopeTriangleCollider.segmentPair(a+(nextA-a)*t,b+(nextB-b)*t,c+(nextC-c)*t,d+(nextD-d)*t)
                    let gap=simd_distance(pair.0,pair.1)-distanceThreshold
                    if gap<=1e-9 {return false}
                    if motion<1e-12 || t>=1 {certified=true;break}
                    t=min(1,t+0.8*gap/motion)
                }
                if !certified {return false}
            }
        }
        return true
    }
}

private extension SIMD4 where Scalar == Double {
    var xyz:SIMD3<Double>{SIMD3(x,y,z)}
}
