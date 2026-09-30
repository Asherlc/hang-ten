import simd

/// Inextensible chain with a coupled mass-metric nonlinear projection. The scalar
/// board-height degree of freedom participates in the same solve as the rope.
struct RopeDynamicsSolver: Sendable {
    // Match inactive-contact feasibility and merit at 10 nm. Physical
    // acceptance separately retains its exact radius/clearance limits.
    private static let contactLinearTolerance=1e-8
    let input:RopePhysicsInput
    let collider:RopeTriangleCollider
    private(set) var state:RopeSimulationState
    private var time=0.0
    private var history:[(Double,Double)]=[]
    private var acceptedMinimumClearance:Double?
    private let channelColliderCache:RopeChannelColliderCache
    private let portalMap:[String:RopePortalRegion]
    private var distanceTension:[[Double]]
    private var lastStepDuration=1.0/240

    /// Return the solver and its first accepted display frame together. Raw
    /// geometry seeds may have separable finite-radius cord overlap; they are
    /// never published before the guarded initialization projection succeeds.
    static func prepareDisplay(input:RopePhysicsInput,state:RopeSimulationState,
                               collider:RopeTriangleCollider) throws -> (solver:Self,frame:RopeFrameSnapshot) {
        var solver=try Self(input:input,state:state,collider:collider)
        let frame=try solver.projectInitialization()
        return (solver,frame)
    }

    init(input:RopePhysicsInput,state:RopeSimulationState,collider:RopeTriangleCollider) throws {
        self.input=input;self.state=state;self.collider=collider
        channelColliderCache=try RopeChannelColliderCache(channels:input.channels)
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

    /// Initialization may separate overlapping finite-radius collars near a
    /// shared support. It never repairs a wood penetration, lost threading or
    /// proper centerline crossing. No trial initialization is displayed.
    mutating func projectInitialization(maxIterations:Int=500) throws -> RopeFrameSnapshot {
        guard maxIterations>0,maxIterations<=2000 else {throw RopePhysicsError.invalid("Invalid initialization bound")}
        var candidate=self
        let preflight=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,
            boardHistory:[state.boardHeight],includeSelfContact:false,channelCache:channelColliderCache)
        guard preflight.geometryAccepted else {throw RopePhysicsError.invalid("Invalid initial wood geometry or threading")}
        for rope in state.ropes {
            guard RopeSimulationMetrics.selfContactPair(positions:rope.positions,radius:rope.radius,
                supports:rope.supports,margin: -2*rope.radius+0.00005+1e-8,restLengths:rope.restLengths)==nil else {
                throw RopePhysicsError.invalid("Initial rope centerline crosses itself")
            }
        }
        for first in state.ropes.indices {
            for second in state.ropes.indices where second>first {
                let radius=state.ropes[first].radius+state.ropes[second].radius
                guard RopeCordContacts.between(state.ropes[first],state.ropes[second],
                    margin: -radius+0.00005+1e-8).isEmpty else {
                    throw RopePhysicsError.invalid("Initial rope centerlines cross each other")
                }
            }
        }
        let prediction=state
        for iteration in 0...maxIterations {
            let metrics=try RopeSimulationMetrics.measure(state:candidate.state,input:input,collider:collider,
                boardHistory:[candidate.state.boardHeight],channelCache:candidate.channelColliderCache)
            if metrics.geometryAccepted {
                if iteration>0 {
                    candidate.history=[(0,candidate.state.boardHeight)]
                    candidate.distanceTension=candidate.state.ropes.map {Array(repeating:0,count:$0.restLengths.count)}
                    for r in candidate.state.ropes.indices {
                        candidate.state.ropes[r].previousPositions=candidate.state.ropes[r].positions
                    }
                }
                candidate.acceptedMinimumClearance=metrics.minimumSegmentClearance
                self=candidate
                return RopeFrameSnapshot(boardHeight:state.boardHeight,orientation:state.orientation,
                    ropes:state.ropes.map{RopeChainSnapshot(id:$0.id,radius:$0.radius,positions:$0.positions)},settled:false,metrics:metrics)
            }
            guard iteration<maxIterations else {break}
            _ = try candidate.correctConstraints(prediction:prediction)
        }
        throw RopePhysicsError.invalid("Initial finite-radius rope contact did not converge")
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
        for first in state.ropes.indices {
            for second in state.ropes.indices where second>first {
                guard RopeCordContacts.sweepValid(previousFirst:old.ropes[first],first:state.ropes[first],
                    previousSecond:old.ropes[second],second:state.ropes[second]) else {
                    throw StepFailure.sweptSelfTraversal
                }
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
        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache)
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
        var secondRope:Int?=nil
        func ropeIndex(_ gradient:Int)->Int {gradient>=2 ? (secondRope ?? rope):rope}
    }

    /// Distance and exact capsule contact share a sparse coupled solve.
    /// CAD wood and eroded portal boundaries constrain sliding crossings
    /// without pinning material. Unilateral tensile contacts are released, with inactive
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
            // Conservative planar sections can lie inside a curved CAD rim.
            // Enforce their aperture separately while keeping material sliding.
            for id in rope.portalCrossings.keys.sorted() {
                guard let crossing=rope.portalCrossings[id],let portal=portalMap[id] else {
                    throw RopePhysicsError.invalid("Missing correction portal")
                }
                let i=crossing.segment
                let boundaries=try RopePassageTopology.boundaryConstraints(from:state.boardPoint(rope.positions[i]),
                    to:state.boardPoint(rope.positions[i+1]),portal:portal,radius:rope.radius)
                for boundary in boundaries where boundary.residual<0.00005 {
                    let gradients=[state.orientation.act(boundary.firstGradient),state.orientation.act(boundary.secondGradient)]
                    let boardGradient = -gradients[0].y-gradients[1].y +
                        (rope.attachments[i] == nil ? 0:gradients[0].y)+(rope.attachments[i+1] == nil ? 0:gradients[1].y)
                    rows.append(ConstraintRow(rope:r,particles:[i,i+1],gradients:gradients,boardGradient:boardGradient,
                        residual:boundary.residual,contact:true,lengthSegment:nil))
                }
            }
            for pair in RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths) {
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
        for first in state.ropes.indices {
            for second in state.ropes.indices where second>first {
                for hit in RopeCordContacts.between(state.ropes[first],state.ropes[second],margin:0.0001) {
                    let i=hit.firstSegment,j=hit.secondSegment,f=hit.firstFraction,g=hit.secondFraction,n=hit.normal
                    let particles=[i,i+1,j,j+1],gradients=[n*(1-f),n*f,-n*(1-g),-n*g]
                    let references=[first,first,second,second]
                    let boardGradient=particles.indices.reduce(0.0) {value,k in
                        value+(state.ropes[references[k]].attachments[particles[k]] == nil ? 0:gradients[k].y)
                    }
                    rows.append(ConstraintRow(rope:first,particles:particles,gradients:gradients,
                        boardGradient:boardGradient,residual:hit.distance-hit.targetDistance,
                        contact:true,lengthSegment:nil,secondRope:second))
                }
            }
        }
        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)
        let selected=solved.ids.map{rows[$0]},lambda=solved.multipliers
        let heightCorrection=solved.height,corrections=solved.particles
        let before=state
        let maximum=corrections.flatMap{$0}.map{simd_length($0)}.max() ?? 0
        var alpha=Self.correctionFraction(ropes:state.ropes,corrections:corrections,heightCorrection:heightCorrection)
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

    /// Bound the relative displacement of each immutable material link. Common
    /// translation preserves link lengths; attached endpoints instead move by
    /// the solved board height, and fixed supports do not move. Global merit,
    /// exact geometry, and continuous collision checks still accept the trial.
    static func correctionFraction(ropes:[RopeChainState],corrections:[[SIMD3<Double>]],heightCorrection:Double)->Double {
        var fraction=1.0
        for r in ropes.indices {
            let rope=ropes[r]
            func displacement(_ particle:Int)->SIMD3<Double> {
                if rope.supports[particle] != nil {return .zero}
                if rope.attachments[particle] != nil {return SIMD3(0,heightCorrection,0)}
                return corrections[r][particle]
            }
            for link in rope.restLengths.indices {
                let relative=simd_length(displacement(link+1)-displacement(link))
                if relative>0 {fraction=min(fraction,0.1*rope.restLengths[link]/relative)}
            }
        }
        return fraction
    }

    private func contactCorrection(rows:[ConstraintRow],weights:[[Double]],prediction:RopeSimulationState) throws
        -> (particles:[[SIMD3<Double>]],height:Double,multipliers:[Double],ids:[Int]) {
        let equalityIDs=rows.indices.filter{!rows[$0].contact}
        let contactIDs=rows.indices.filter{rows[$0].contact}
        let backbone=try constraintBackbone(rows:equalityIDs.map{rows[$0]},weights:weights,prediction:prediction)
        let variables=backbone.variables
        let contacts=contactIDs.map {id -> RopeLinearContact in
            let row=rows[id]
            var indices:[Int]=[],coefficients:[Double]=[]
            for k in row.particles.indices {for axis in 0..<3 {
                let variable=variables[row.ropeIndex(k)][row.particles[k]][axis]
                if variable>=0 {indices.append(variable);coefficients.append(row.gradients[k][axis])}
            }}
            return RopeLinearContact(indices:indices,coefficients:coefficients,border:[row.boardGradient],residual:row.residual)
        }
        let solved:RopeContactSystem.Solution
        do {
            solved=try RopeContactSystem.solve(factor:backbone.factor,base:backbone.base,border:backbone.border,
                contacts:contacts,maxIterations:min(2048,rows.count*2+10),fallback:{
                    let direct=try fullContactCorrection(rows:rows,weights:weights,prediction:prediction)
                    var base=backbone.base
                    for r in weights.indices {for i in weights[r].indices where weights[r][i]>0 {
                        let v=variables[r][i]
                        for axis in 0..<3 {base[v[axis]]=direct.particles[r][i][axis]}
                    }}
                    var allMultipliers=Array(repeating:0.0,count:rows.count)
                    for (index,id) in direct.ids.enumerated() {allMultipliers[id]=direct.multipliers[index]}
                    for (index,id) in equalityIDs.enumerated() {base[backbone.rowVariables[index]!]=allMultipliers[id]}
                    let active=Set(direct.ids)
                    return RopeContactSystem.Solution(base:base,border:[direct.height],
                        multipliers:contactIDs.map{allMultipliers[$0]},activeIDs:contactIDs.indices.filter{active.contains(contactIDs[$0])})
                })
        } catch RopeContactSystem.Failure.iterationLimit {throw StepFailure.nonlinearConvergence}
        var particles=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
        for r in weights.indices {for i in weights[r].indices where weights[r][i]>0 {
            let v=variables[r][i];particles[r][i]=SIMD3(solved.base[v.x],solved.base[v.y],solved.base[v.z])
        }}
        var multipliers=Array(repeating:0.0,count:rows.count)
        for (index,id) in equalityIDs.enumerated() {multipliers[id]=solved.base[backbone.rowVariables[index]!]}
        for index in contactIDs.indices {multipliers[contactIDs[index]]=solved.multipliers[index]}
        let ids=(equalityIDs+solved.activeIDs.map{contactIDs[$0]}).sorted()
        return (particles,solved.border[0],ids.map{multipliers[$0]},ids)
    }

    /// Preserve the explicitly regularized KKT path for contact Schur
    /// conditioning failures. Complete inactive separation remains mandatory.
    private func fullContactCorrection(rows:[ConstraintRow],weights:[[Double]],prediction:RopeSimulationState) throws
        -> (particles:[[SIMD3<Double>]],height:Double,multipliers:[Double],ids:[Int]) {
        var working=RopeContactWorkingSet(activeIDs:rows.indices.filter{!rows[$0].contact})
        for _ in 0..<min(2048,rows.count*2+10) {
            let ids=working.activeIDs,selected=ids.map{rows[$0]}
            let solved=try constraintBackbone(rows:selected,weights:weights,prediction:prediction)
            let lambda=solved.multipliers
            if working.releaseTensileContact(multipliers:lambda,contacts:selected.map{$0.contact}) {continue}
            var particles=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
            for r in weights.indices {for i in weights[r].indices where weights[r][i]>0 {
                let v=solved.variables[r][i];particles[r][i]=SIMD3(solved.base[v.x],solved.base[v.y],solved.base[v.z])
            }}
            let height=solved.border[0]
            var active=Array(repeating:false,count:rows.count)
            for id in ids {active[id]=true}
            var worst:(Int,Double)?
            for index in rows.indices where rows[index].contact && !active[index] {
                let row=rows[index]
                var residual=row.residual+row.boardGradient*height
                for k in row.particles.indices {residual += simd_dot(row.gradients[k],particles[row.ropeIndex(k)][row.particles[k]])}
                if residual < -Self.contactLinearTolerance && residual<(worst?.1 ?? 0) {worst=(index,residual)}
            }
            if let index=worst?.0 {working.insert(index);continue}
            return (particles,height,lambda,ids)
        }
        throw StepFailure.nonlinearConvergence
    }

    /// Primal KKT system: particle inertia plus tension curvature, local
    /// length/contact rows, and borders for height/nonlocal self-contact.
    private func constraintBackbone(rows:[ConstraintRow],weights:[[Double]],prediction:RopeSimulationState) throws
        -> (factor:RopeBandedFactorization,variables:[[SIMD3<Int>]],rowVariables:[Int:Int],base:[Double],border:[Double],multipliers:[Double]) {
        let borderRows=rows.indices.filter{rows[$0].secondRope != nil || rows[$0].particles.max()!-rows[$0].particles.min()!>1}
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
                for axis in 0..<3 where variables[row.ropeIndex(j)][row.particles[j]][axis]>=0 {
                    try system.addSymmetric(row:variable,column:variables[row.ropeIndex(j)][row.particles[j]][axis],value:row.gradients[j][axis])
                }
            }
        }
        for (offset,index) in borderRows.enumerated() {
            let row=rows[index],variable=offset+1
            border[variable][variable] = -1e-8
            border[0][variable]=row.boardGradient;border[variable][0]=row.boardGradient
            borderRHS[variable] = -row.residual
            for j in row.particles.indices {
                for axis in 0..<3 where variables[row.ropeIndex(j)][row.particles[j]][axis]>=0 {
                    columns[variable][variables[row.ropeIndex(j)][row.particles[j]][axis]] += row.gradients[j][axis]
                }
            }
        }
        let factor=try system.factorized(borderColumns:columns,borderMatrix:border)
        let solved=try factor.solve(rhs:rhs,borderRHS:borderRHS)
        var multipliers=Array(repeating:0.0,count:rows.count)
        for index in local {multipliers[index]=solved.base[rowVariables[index]!]}
        for (offset,index) in borderRows.enumerated() {multipliers[index]=solved.border[offset+1]}
        return (factor,variables,rowVariables,solved.base,solved.border,multipliers)
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
                violation += max(0,(hits.map{$0.penetrationDepth}.max() ?? 0)-Self.contactLinearTolerance)
            }
            for pair in RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths) {
                let points=RopeTriangleCollider.segmentPair(rope.positions[pair.x],rope.positions[pair.x+1],rope.positions[pair.y],rope.positions[pair.y+1])
                violation += max(0,2*rope.radius+0.00005-simd_distance(points.0,points.1)-Self.contactLinearTolerance)
            }
            for (id,crossing) in rope.portalCrossings {
                guard let portal=portalMap[id] else{throw RopePhysicsError.invalid("Missing merit portal")}
                let margin=RopePassageTopology.boundaryMargin(candidate.boardPoint(crossing.point(in:rope.positions)),portal:portal)
                violation += max(0,rope.radius+RopeRegionGeometry.clearance-margin-Self.contactLinearTolerance)
            }
        }
        for first in candidate.ropes.indices {
            for second in candidate.ropes.indices where second>first {
                for contact in RopeCordContacts.between(candidate.ropes[first],candidate.ropes[second],margin:0.0001) {
                    violation += max(0,contact.targetDistance-contact.distance-Self.contactLinearTolerance)
                }
            }
        }
        return objective+penalty*violation
    }

}

enum RopeMotionSweep {
    /// A lower bound for the separation of two truncated rays leaving the
    /// same fixed support throughout linear endpoint motion. Bound sin(theta)
    /// by the cross-product norm, and each ray's radius by its chord minimum.
    static func sharedSupportSeparationBound(previousFirst:SIMD3<Double>,first:SIMD3<Double>,
        previousSecond:SIMD3<Double>,second:SIMD3<Double>,firstFraction:Double,secondFraction:Double)->Double {
        guard firstFraction>0,firstFraction<=1,secondFraction>0,secondFraction<=1 else {return 0}
        let du=first-previousFirst,dv=second-previousSecond
        func minimumNorm(_ origin:SIMD3<Double>,_ delta:SIMD3<Double>)->Double {
            let square=simd_length_squared(delta)
            let t=square>1e-30 ? min(1,max(0,-simd_dot(origin,delta)/square)):0
            return simd_length(origin+delta*t)
        }
        let minimumFirst=firstFraction*minimumNorm(previousFirst,du)
        let minimumSecond=secondFraction*minimumNorm(previousSecond,dv)
        let maxFirst=max(simd_length(previousFirst),simd_length(first))
        let maxSecond=max(simd_length(previousSecond),simd_length(second))
        guard maxFirst.isFinite,maxSecond.isFinite,maxFirst>1e-12,maxSecond>1e-12 else {return 0}
        let midpointFirst=(previousFirst+first)/2,midpointSecond=(previousSecond+second)/2
        let midpointCross=simd_length(simd_cross(midpointFirst,midpointSecond))
        // The cross-product derivative is affine, so its norm is bounded
        // by its two endpoints across the complete unit interval.
        let derivative=max(simd_length(simd_cross(du,previousSecond)+simd_cross(previousFirst,dv)),
            simd_length(simd_cross(du,second)+simd_cross(first,dv)))
        let crossLower=max(0,midpointCross-derivative/2)
        let sineLower=min(1,crossLower/(maxFirst*maxSecond))
        return max(0,max(minimumFirst,minimumSecond)*sineLower-1e-12)
    }


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
                if knot,i==0,j==links-1,let support=common,
                   a==support,d==support,nextA==support,nextD==support {
                    let bound=sharedSupportSeparationBound(previousFirst:b-support,first:nextB-support,
                        previousSecond:c-support,second:nextC-support,
                        firstFraction:min(1,1e-6/restLengths[i]),secondFraction:min(1,1e-6/restLengths[j]))
                    if bound>distanceThreshold+1e-9 {continue}
                }
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
                // The final advancement can reach t=1 on the last allowed
                // iteration. Test that endpoint before reporting exhaustion.
                if !certified && t>=1 {
                    let pair=RopeTriangleCollider.segmentPair(nextA,nextB,nextC,nextD)
                    certified=simd_distance(pair.0,pair.1)-distanceThreshold>1e-9
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

/// Working set for unilateral contacts; multipliers are compressive at <= 0.
/// Full working-set solutions may have tensile multipliers. Move from the
/// retained dual-feasible point only to the first zero multiplier, release
/// that blocking row, and solve again. Dropping the greatest tensile row
/// without this blocking step can repeatedly revisit the same working sets.
struct RopeContactWorkingSet {
    var activeIDs:[Int]
    private var feasibleMultipliers:[Int:Double]=[:]

    init(activeIDs:[Int]) {self.activeIDs=activeIDs}
    mutating func insert(_ id:Int) {activeIDs.append(id);activeIDs.sort()}

    mutating func releaseTensileContact(multipliers:[Double],contacts:[Bool])->Bool {
        var blocking:(index:Int,fraction:Double)?
        for j in activeIDs.indices where contacts[j] && multipliers[j]>1e-12 {
            let previous=min(0,feasibleMultipliers[activeIDs[j]] ?? 0)
            let fraction=max(0,min(1,-previous/(multipliers[j]-previous)))
            if fraction<(blocking?.fraction ?? 2) {blocking=(j,fraction)}
        }
        if let blocking {
            for j in activeIDs.indices {
                let id=activeIDs[j],previous=feasibleMultipliers[id] ?? 0
                feasibleMultipliers[id]=previous+blocking.fraction*(multipliers[j]-previous)
            }
            feasibleMultipliers.removeValue(forKey:activeIDs[blocking.index])
            activeIDs.remove(at:blocking.index)
            return true
        }
        for j in activeIDs.indices {feasibleMultipliers[activeIDs[j]]=multipliers[j]}
        return false
    }
}
