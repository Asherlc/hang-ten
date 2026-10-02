import Foundation

// Experimental numerically differentiated contact curvature; not linked to app.
extension RopeDynamicsSolver {
    private mutating func curvatureCorrect(prediction:RopeSimulationState) throws {
        let initial=state,eps=NonlinearPrimalDual.epsilon
        let weights=state.ropes.map {rope in rope.positions.indices.map {i -> Double in
            if rope.supports[i] != nil || rope.attachments[i] != nil {return 0}
            let length=(i>0 ? rope.restLengths[i-1]:0)+(i<rope.restLengths.count ? rope.restLengths[i]:0)
            return 2/(rope.linearMass*length)
        }}
        var variable=state.ropes.map{Array<Int?>(repeating:nil,count:$0.positions.count)}
        var lengthVariable=state.ropes.map{Array(repeating:0,count:$0.restLengths.count)}
        var size=0,equalities:Set<Int>=[]
        for r in state.ropes.indices {for i in state.ropes[r].positions.indices {
            if weights[r][i]>0 {variable[r][i]=size;size += 3}
            if i<lengthVariable[r].count {lengthVariable[r][i]=size;equalities.insert(size);size += 1}
        }}
        let height=size;size += 1
        var coordinateRefs=Array<(Int,Int,Int)?>(repeating:nil,count:size)
        for r in variable.indices {for i in variable[r].indices {if let base=variable[r][i] {
            for axis in 0..<3 {coordinateRefs[base+axis]=(r,i,axis)}
        }}}
        let minimumRest=state.ropes.flatMap{$0.restLengths}.min()!
        var masses=Array(repeating:0.0,count:size)
        for r in variable.indices {for i in variable[r].indices {if let base=variable[r][i] {
            for axis in 0..<3 {masses[base+axis]=1/weights[r][i]}
        }}}
        masses[height]=state.boardMass
        var terms:[AugmentedTerm]=[],keys:Set<String>=[],slacks:[Double]=[],initialS:[Double]=[]
        var lastMovement=Double.infinity
        func coefficients(_ row:AugmentedRow)->[(Int,Double)] {
            var combined:[Int:Double]=[:]
            for k in row.refs.indices {let (r,i)=row.refs[k];if let base=variable[r][i] {
                for axis in 0..<3 {combined[base+axis,default:0] += row.gradients[k][axis]}
            }}
            combined[height,default:0] += row.height
            return combined.keys.sorted().compactMap{combined[$0]! == 0 ? nil:($0,combined[$0]!)}
        }
        func equalityVariable(_ feature:AugmentedFeature)->Int? {
            if case .length(let r,let i)=feature {return lengthVariable[r][i]}
            return nil
        }
        func evaluate(_ solver:RopeDynamicsSolver,_ current:[AugmentedTerm],_ v:[Double]) throws ->
            (rows:[AugmentedRow],jacobians:[[(Int,Double)]],a:[Double],b:[Double],h:[Double],score:Double,certificate:[String:Double],trace:[[String:Any]]) {
            guard current.count==v.count,current.count==initialS.count else {
                throw RopePhysicsError.invalid("Interrupted nonlinear contact initialization")
            }
            var a=Array(repeating:0.0,count:size)
            for r in variable.indices {for i in variable[r].indices {if let base=variable[r][i] {
                let offset=solver.state.ropes[r].positions[i]-prediction.ropes[r].positions[i]
                for axis in 0..<3 {a[base+axis]=masses[base+axis]*offset[axis]}
            }}}
            a[height]=masses[height]*(solver.state.boardHeight-prediction.boardHeight)
            var rows:[AugmentedRow]=[],jacobians:[[(Int,Double)]]=[],b=Array(repeating:0.0,count:current.count),h=b
            var score=0.0,equality=0.0,minC=0.0,minGap=0.0,complementarity=0.0,internalComplementarity=0.0
            var trace:[[String:Any]]=[]
            for k in current.indices {
                let term=current[k],row=try solver.augmentedRow(term.feature),j=coefficients(row),gap=row.residual-eps*term.dual
                rows.append(row);jacobians.append(j)
                for (index,value) in j {a[index] += value*term.dual}
                if row.contact {
                    let s = -term.dual
                    guard s>0,v[k]>0,s.isFinite,v[k].isFinite else {throw RopePhysicsError.invalid("Nonpositive nonlinear contact force/slack")}
                    h[k]=gap-v[k]
                    score += pow(h[k]/term.scale,2)+pow(s*v[k]/(initialS[k]*term.scale),2)
                    minC=min(minC,row.residual);minGap=min(minGap,gap)
                    complementarity=max(complementarity,abs(s*gap));internalComplementarity=max(internalComplementarity,s*v[k])
                } else {
                    b[k]=gap;equality=max(equality,abs(gap));score += pow(gap/term.scale,2)
                }
                trace.append(["key":term.key,"C":row.residual,"lambda":term.dual,"v":v[k],"gap":gap,"h":h[k],"contact":row.contact,
                    "scale":term.scale,"initialS":initialS[k],"references":row.refs.map{[$0.0,$0.1]},"gradients":row.gradients.map{[$0.x,$0.y,$0.z]},
                    "heightGradient":row.height,"jacobian":j.map{[Double($0.0),$0.1]}])
            }
            for i in masses.indices where masses[i]>0 {score += pow(a[i]/(masses[i]*minimumRest),2)}
            guard score.isFinite,a.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite nonlinear residual")}
            return (rows,jacobians,a,b,h,score,["stationarity":a.map{abs($0)}.max() ?? 0,"equality":equality,"minC":minC,
                "minGap":minGap,"complementarity":complementarity,"internalComplementarity":internalComplementarity],trace)
        }
        defer {
            var result:[String:Any]=["phase":"return-or-rejection","state":AugmentedTrace.points(state),"proposalCheckpoint":foundationCheckpoint()]
            if let e=try? evaluate(self,terms,slacks) {result["terms"]=e.trace;result["certificate"]=e.certificate;result["score"]=e.score}
            else {result["partialTermKeys"]=terms.map{$0.key};result["initializedSlackCount"]=slacks.count}
            PrimalDualTrace.phases.append(result)
        }
        PrimalDualTrace.phases.append(["phase":"prediction","state":AugmentedTrace.points(state),"checkpoint":foundationCheckpoint(),
            "variable":variable.map{$0.map{$0 as Any? ?? NSNull()}},"lengthVariable":lengthVariable,"heightVariable":height,"masses":masses,"minimumRest":minimumRest])
        for iteration in 0...16 {
            try AugmentedTrace.budget()
            let discoveryStart=ProcessInfo.processInfo.systemUptime,oldCount=terms.count
            try augmentedDiscover(&terms,&keys,weights:weights)
            for k in oldCount..<terms.count {
                let row=try augmentedRow(terms[k].feature)
                if row.contact {
                    let s=terms[k].scale*terms[k].startPenalty
                    terms[k].dual = -s
                    slacks.append(max(row.residual+eps*s,terms[k].scale));initialS.append(s)
                } else {slacks.append(0);initialS.append(0)}
            }
            let discoverySeconds=ProcessInfo.processInfo.systemUptime-discoveryStart
            let e=try evaluate(self,terms,slacks),c=e.certificate
            PrimalDualTrace.phases.append(["phase":"iteration","iteration":iteration,"state":AugmentedTrace.points(state),"terms":e.trace,
                "a":e.a,"b":e.b,"h":e.h,"score":e.score,"certificate":c,"admitted":terms.count-oldCount,
                "discoverySeconds":discoverySeconds,"movement":lastMovement.isFinite ? lastMovement:NSNull(),"strain":maximumStrain()])
            let certified=c["stationarity"]!<=1e-10 && c["equality"]!<=1e-8 && c["minC"]!>=(-1e-8) && c["minGap"]!>=(-1e-10)
                && c["complementarity"]!<=1e-14 && c["internalComplementarity"]!<=1e-18
            if certified && maximumStrain()<0.0002 && lastMovement<1e-8 {
                let penalty=max(1,2*(terms.map{abs($0.dual)}.max() ?? 0))
                let before=try augmentedMeritParts(initial,prediction:prediction,weights:weights,penalty:penalty)
                let after=try augmentedMeritParts(state,prediction:prediction,weights:weights,penalty:penalty)
                let exactBefore=try merit(initial,prediction:prediction,weights:weights,penalty:penalty)
                let exactAfter=try merit(state,prediction:prediction,weights:weights,penalty:penalty)
                guard abs(exactBefore-before["total"]!)<=1e-18,abs(exactAfter-after["total"]!)<=1e-18,exactAfter<=exactBefore+1e-18 else {
                    throw RopePhysicsError.invalid("Original nonlinear global merit rejected")
                }
                PrimalDualTrace.phases.append(["phase":"certified-before-original-step-guards","meritBefore":before,"meritAfter":after])
                for term in terms {if case .length(let r,let i)=term.feature {distanceTension[r][i]=max(0,term.dual)}}
                return
            }
            guard iteration<16 else {throw RopePhysicsError.invalid("Fixed sixteen-update nonlinear primal-dual certificate/convergence cap")}
            let assemblyStart=ProcessInfo.processInfo.systemUptime
            var entries:[(Int,Int,Double)]=[]
            for i in masses.indices where masses[i]>0 {entries.append((i,i,masses[i]))}
            for i in equalities.sorted() {entries.append((i,i,-eps))}
            var diagonals=Array(repeating:0.0,count:terms.count)
            var curvatureTrace:[[String:Any]]=[]
            var curvatureSeconds=0.0
            for k in terms.indices {
                let j=e.jacobians[k]
                if e.rows[k].contact {
                    let elim=try NonlinearPrimalDual.eliminate(s:-terms[k].dual,v:slacks[k],h:e.h[k],rc:0)
                    diagonals[k]=elim.diagonal
                    for u in j.indices {for v in 0...u {entries.append((j[u].0,j[v].0,elim.diagonal*j[u].1*j[v].1))}}
                    try AugmentedTrace.budget()
                    let curvatureStart=ProcessInfo.processInfo.systemUptime,curvatureOrigin=state
                    var active:Set<Int>=[]
                    for (r,i) in e.rows[k].refs {
                        if let base=variable[r][i] {for axis in 0..<3 {active.insert(base+axis)}}
                        if state.ropes[r].attachments[i] != nil {active.insert(height)}
                    }
                    switch terms[k].feature {case .wood,.portal:active.insert(height);default:break}
                    let ids=active.sorted(),feature=terms[k].feature
                    let curvature=try NonlinearContactCurvature.hessian(count:ids.count,minimumRest:minimumRest) {axis,change in
                        defer {state=curvatureOrigin}
                        state=curvatureOrigin
                        let index=ids[axis]
                        if index==height {
                            state.boardHeight += change
                            for r in state.ropes.indices {for (i,local) in state.ropes[r].attachments {state.ropes[r].positions[i]=state.worldPoint(local)}}
                        } else {
                            guard let (r,i,coordinate)=coordinateRefs[index] else {throw RopePhysicsError.invalid("Invalid contact curvature coordinate")}
                            state.ropes[r].positions[i][coordinate] += change
                        }
                        let changed=try augmentedRow(feature),values=Dictionary(uniqueKeysWithValues:coefficients(changed))
                        return ids.map{values[$0] ?? 0}
                    }
                    for u in ids.indices {for v in 0...u {entries.append((ids[u],ids[v],terms[k].dual*curvature.matrix[u][v]))}}
                    curvatureTrace.append(["key":terms[k].key,"variables":ids,"hessian":curvature.matrix,"rawHessian":curvature.raw,"rawAsymmetry":curvature.asymmetry])
                    curvatureSeconds += ProcessInfo.processInfo.systemUptime-curvatureStart
                } else if let lambda=equalityVariable(terms[k].feature) {
                    for (index,value) in j {entries.append((index,lambda,value))}
                    if case .length(let r,let i)=terms[k].feature,terms[k].dual != 0 {
                        let rope=state.ropes[r],delta=rope.positions[i+1]-rope.positions[i],length=simd_length(delta),n=delta/length
                        var derivatives:[Int:SIMD3<Double>]=[:]
                        if let base=variable[r][i] {for axis in 0..<3 {var v=SIMD3<Double>.zero;v[axis] = -1;derivatives[base+axis]=v}}
                        if let base=variable[r][i+1] {for axis in 0..<3 {var v=SIMD3<Double>.zero;v[axis]=1;derivatives[base+axis]=v}}
                        let attachedA=rope.attachments[i] != nil,attachedB=rope.attachments[i+1] != nil
                        if attachedA != attachedB {derivatives[height]=SIMD3(0,attachedB ? 1 : -1,0)}
                        let ids=derivatives.keys.sorted(),factor=terms[k].dual/length
                        for u in ids.indices {for v in 0...u {
                            let a=derivatives[ids[u]]!,b=derivatives[ids[v]]!
                            entries.append((ids[u],ids[v],factor*(simd_dot(a,b)-simd_dot(a,n)*simd_dot(b,n))))
                        }}
                    }
                }
            }
            let assemblySeconds=ProcessInfo.processInfo.systemUptime-assemblyStart,factorStart=ProcessInfo.processInfo.systemUptime
            let factor=try NonlinearPrimalDualFactor(size:size,equalities:equalities,entries:entries)
            let factorSeconds=ProcessInfo.processInfo.systemUptime-factorStart
            func direction(_ rc:[Double]) throws -> (x:[Double],s:[Double],v:[Double],lambda:[Double],rhs:[Double]) {
                var rhs=e.a.map(-),ds=Array(repeating:0.0,count:terms.count),dv=ds,dl=ds
                for k in terms.indices {
                    if e.rows[k].contact {
                        let elim=try NonlinearPrimalDual.eliminate(s:-terms[k].dual,v:slacks[k],h:e.h[k],rc:rc[k])
                        for (index,value) in e.jacobians[k] {rhs[index] += value*elim.load}
                    } else if let index=equalityVariable(terms[k].feature) {rhs[index] = -e.b[k]}
                }
                let x=try factor.solve(rhs)
                for k in terms.indices {
                    if e.rows[k].contact {
                        let jdx=e.jacobians[k].reduce(0.0){$0+$1.1*x[$1.0]}
                        let d=try NonlinearPrimalDual.recover(s:-terms[k].dual,v:slacks[k],h:e.h[k],rc:rc[k],jdx:jdx)
                        ds[k]=d.s;dv[k]=d.v
                    } else if let index=equalityVariable(terms[k].feature) {dl[k]=x[index]}
                }
                return (x,ds,dv,dl,rhs)
            }
            let contactIDs=terms.indices.filter{e.rows[$0].contact},s=contactIDs.map{-terms[$0].dual},v=contactIDs.map{slacks[$0]}
            guard !contactIDs.isEmpty else {throw RopePhysicsError.invalid("Loaded checkpoint unexpectedly has no contact rows")}
            let solveStart=ProcessInfo.processInfo.systemUptime
            var rc=terms.indices.map{e.rows[$0].contact ? terms[$0].dual*slacks[$0]:0}
            let affine=try direction(rc)
            let ap=try NonlinearPrimalDual.fraction(values:s,change:contactIDs.map{affine.s[$0]},safety:1)
            let ad=try NonlinearPrimalDual.fraction(values:v,change:contactIDs.map{affine.v[$0]},safety:1)
            let mu=zip(s,v).reduce(0.0){$0+$1.0*$1.1}/Double(s.count)
            let muAff=contactIDs.reduce(0.0){$0+(-terms[$1].dual+ap*affine.s[$1])*(slacks[$1]+ad*affine.v[$1])}/Double(s.count)
            let sigma=pow(min(1,max(0,muAff/mu)),3)
            for k in contactIDs {rc[k]=sigma*mu+terms[k].dual*slacks[k]-affine.s[k]*affine.v[k]}
            let d=try direction(rc),solveSeconds=ProcessInfo.processInfo.systemUptime-solveStart
            var corrections=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
            for r in variable.indices {for i in variable[r].indices {if let base=variable[r][i] {corrections[r][i]=SIMD3(d.x[base],d.x[base+1],d.x[base+2])}}}
            var alpha=min(try NonlinearPrimalDual.fraction(values:s,change:contactIDs.map{d.s[$0]},safety:0.995),
                try NonlinearPrimalDual.fraction(values:v,change:contactIDs.map{d.v[$0]},safety:0.995))
            alpha=min(alpha,Self.correctionFraction(ropes:state.ropes,corrections:corrections,heightCorrection:d.x[height]))
            let old=state,oldTerms=terms,oldSlacks=slacks
            var trials:[[String:Any]]=[],accepted=false
            for trial in 0..<16 {
                try AugmentedTrace.budget()
                state=old;terms=oldTerms;slacks=oldSlacks
                state.boardHeight += alpha*d.x[height]
                for r in state.ropes.indices {for i in state.ropes[r].positions.indices {
                    if let local=state.ropes[r].attachments[i] {state.ropes[r].positions[i]=state.worldPoint(local)}
                    else {state.ropes[r].positions[i] += alpha*corrections[r][i]}
                }}
                for k in terms.indices {
                    if e.rows[k].contact {terms[k].dual -= alpha*d.s[k];slacks[k] += alpha*d.v[k]}
                    else {terms[k].dual += alpha*d.lambda[k]}
                }
                do {
                    try RopePassageTopology.refresh(state:&state,input:input)
                    for rope in state.ropes {for point in rope.positions {
                        guard !collider.augmentedContains(state.boardPoint(point)) else {throw RopePhysicsError.invalid("Nonlinear trial entered wood")}
                    }}
                    let next=try evaluate(self,terms,slacks)
                    trials.append(["trial":trial,"alpha":alpha,"score":next.score,"state":AugmentedTrace.points(state)])
                    if next.score<=(1-1e-4*alpha)*e.score {accepted=true;break}
                } catch RopePhysicsError.invalid(let reason) {trials.append(["trial":trial,"alpha":alpha,"invalid":reason,"state":AugmentedTrace.points(state)])}
                alpha *= 0.5
            }
            PrimalDualTrace.phases.append(["phase":"direction","iteration":iteration,"entries":entries.map{[Double($0.0),Double($0.1),$0.2]},
                "affineX":affine.x,"affineS":affine.s,"affineV":affine.v,"affineRHS":affine.rhs,"rc":rc,"x":d.x,"s":d.s,"v":d.v,
                "lambda":d.lambda,"rhs":d.rhs,"mu":mu,"muAffine":muAff,"sigma":sigma,"affineFractionS":ap,"affineFractionV":ad,
                "accepted":accepted,"trials":trials,"assemblySeconds":assemblySeconds,"factorSeconds":factorSeconds,"solveSeconds":solveSeconds,
                "curvature":curvatureTrace,"curvatureSeconds":curvatureSeconds,
                "backend":factor.backend,"solveCalls":factor.solveCalls,"refinementSolves":factor.refinementSolves,"maximumMatrixResidual":factor.maximumResidual])
            guard accepted else {throw RopePhysicsError.invalid("Fixed nonlinear primal-dual line search exhausted")}
            lastMovement=abs(state.boardHeight-old.boardHeight)
            for r in state.ropes.indices {for i in state.ropes[r].positions.indices {lastMovement=max(lastMovement,simd_distance(state.ropes[r].positions[i],old.ropes[r].positions[i]))}}
        }
    }
}
