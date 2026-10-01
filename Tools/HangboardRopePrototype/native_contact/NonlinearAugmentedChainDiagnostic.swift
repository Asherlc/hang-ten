import Foundation

// Appended only to the already retained native Dynamics source snapshot.
// Exactly one direction from a rejected state; it cannot publish a frame.
extension RopeDynamicsSolver {
    mutating func augmentedChainDiagnostic(final:[String:Any],predictionData:[String:Any]) throws -> [String:Any] {
        let started=ProcessInfo.processInfo.systemUptime
        let old=state
        defer {state=old}
        let records=final["terms"] as! [[String:Any]]
        var prediction=state
        prediction.boardHeight=predictionData["height"] as! Double
        let predictionPoints=predictionData["positions"] as! [[[Double]]]
        for r in prediction.ropes.indices {prediction.ropes[r].positions=predictionPoints[r].map{SIMD3($0[0],$0[1],$0[2])}}
        func feature(_ record:[String:Any]) throws -> AugmentedFeature {
            let parts=(record["key"] as! String).split(separator:":").map(String.init)
            let r=Int(parts[1])!,i=Int(parts[2])
            switch parts[0] {
            case "length":return .length(r,i!)
            case "point":return .wood(r,i!,i!,Int(parts[3])!)
            case "link":return .wood(r,i!,i!+1,Int(parts[3])!)
            case "portal":return .portal(r,parts[2..<(parts.count-1)].joined(separator:":"),Int(parts.last!)!)
            default:throw RopePhysicsError.invalid("Single diagnostic refuses unsupported nonlocal feature")
            }
        }
        let features=try records.map(feature)
        let weights=state.ropes.map {rope in rope.positions.indices.map {i -> Double in
            if rope.supports[i] != nil || rope.attachments[i] != nil {return 0}
            let length=(i>0 ? rope.restLengths[i-1]:0)+(i<rope.restLengths.count ? rope.restLengths[i]:0)
            return 2/(rope.linearMass*length)
        }}
        var variables=state.ropes.map{Array<Int?>(repeating:nil,count:$0.positions.count)},size=0
        for r in state.ropes.indices {for i in state.ropes[r].positions.indices where weights[r][i]>0 {variables[r][i]=size;size += 3}}
        let height=size
        var masses=Array(repeating:state.boardMass,count:size+1),offset=Array(repeating:0.0,count:size+1)
        for r in state.ropes.indices {for i in state.ropes[r].positions.indices {if let index=variables[r][i] {
            let d=state.ropes[r].positions[i]-prediction.ropes[r].positions[i]
            for axis in 0..<3 {masses[index+axis]=1/weights[r][i];offset[index+axis]=d[axis]}
        }}}
        offset[height]=state.boardHeight-prediction.boardHeight
        var band=try RopeBandedSystem(size:size,bandwidth:5),border=Array(repeating:0.0,count:size)
        var heightHessian=masses[height],gradient=zip(masses,offset).map(*)
        for index in 0..<size {try band.addSymmetric(row:index,column:index,value:masses[index])}
        var sparse:[[(Int,Double)]]=[],curvatures:[Double]=[],forces:[Double]=[]
        for index in features.indices {
            let row=try augmentedRow(features[index])
            guard abs(row.residual-(records[index]["C"] as! Double))<=1e-15 else {throw RopePhysicsError.invalid("Retained nonlinear feature residual changed on restore")}
            let dual=records[index]["lambda"] as! Double,penalty=records[index]["rho"] as! Double
            let t=try NonlinearAugmented.force(row.residual,dual:dual,penalty:penalty,contact:row.contact)
            let k=try NonlinearAugmented.curvature(row.residual,dual:dual,penalty:penalty,contact:row.contact)
            var combined:[Int:Double]=[height:row.height]
            for j in row.refs.indices {let (r,i)=row.refs[j];if let variable=variables[r][i] {for axis in 0..<3 {combined[variable+axis,default:0] += row.gradients[j][axis]}}}
            let coefficients=combined.keys.sorted().compactMap{combined[$0] == 0 ? nil:($0,combined[$0]!)}
            sparse.append(coefficients);curvatures.append(k);forces.append(t)
            for (i,a) in coefficients {
                gradient[i] += t*a
                for (j,b) in coefficients where j<=i {
                    if i==height {if j==height {heightHessian += k*a*b}else {border[j] += k*a*b}}
                    else {try band.addSymmetric(row:i,column:j,value:k*a*b)}
                }
            }
        }
        let assemblySeconds=ProcessInfo.processInfo.systemUptime-started
        let factorStart=ProcessInfo.processInfo.systemUptime
        let factor=try band.factorized(borderColumns:[border],borderMatrix:[[heightHessian]])
        let factorSeconds=ProcessInfo.processInfo.systemUptime-factorStart
        let solveStart=ProcessInfo.processInfo.systemUptime
        let solved=try factor.solve(rhs:Array(gradient.prefix(size)).map{-$0},borderRHS:[-gradient[height]])
        let solveSeconds=ProcessInfo.processInfo.systemUptime-solveStart
        let direction=solved.base+solved.border
        var residual=zip(masses,direction).map(*)
        for index in sparse.indices {
            let jdx=sparse[index].reduce(0.0){$0+$1.1*direction[$1.0]}
            for (i,a) in sparse[index] {residual[i] += curvatures[index]*a*jdx}
        }
        let residualMax=zip(residual,gradient).map{abs($0+$1)}.max()!
        let derivative=zip(gradient,direction).reduce(0.0){$0+$1.0*$1.1}
        guard residualMax<=1e-10,derivative<0 else {throw RopePhysicsError.invalid("Single global augmented direction failed Newton certificate/descent")}
        var corrections=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
        for r in state.ropes.indices {for i in state.ropes[r].positions.indices {if let index=variables[r][i] {corrections[r][i]=SIMD3(direction[index],direction[index+1],direction[index+2])}}}
        let dh=direction[height]
        func energy(_ solver:RopeDynamicsSolver) throws -> Double {
            var value=0.5*state.boardMass*pow(solver.state.boardHeight-prediction.boardHeight,2)
            for r in solver.state.ropes.indices {for i in solver.state.ropes[r].positions.indices where weights[r][i]>0 {
                value += 0.5*simd_length_squared(solver.state.ropes[r].positions[i]-prediction.ropes[r].positions[i])/weights[r][i]
            }}
            for index in features.indices {
                let row=try solver.augmentedRow(features[index])
                value += try NonlinearAugmented.energy(row.residual,dual:records[index]["lambda"] as! Double,penalty:records[index]["rho"] as! Double,contact:row.contact)
            }
            return value
        }
        func lengths(_ solver:RopeDynamicsSolver)->[String:Double] {
            let errors=solver.state.ropes.flatMap{rope in rope.restLengths.indices.map{simd_distance(rope.positions[$0],rope.positions[$0+1])-rope.restLengths[$0]}}
            return ["rms":sqrt(errors.reduce(0.0){$0+$1*$1}/Double(errors.count)),"peakStrain":solver.maximumStrain(),"l1":errors.reduce(0.0){$0+abs($1)}]
        }
        let initialEnergy=try energy(self),initialLengths=lengths(self)
        let initialMerit=try augmentedMeritParts(state,prediction:prediction,weights:weights,penalty:1)
        var alpha=Self.correctionFraction(ropes:state.ropes,corrections:corrections,heightCorrection:dh)
        var trials:[[String:Any]]=[],accepted=false
        for trial in 0..<16 {
            guard ProcessInfo.processInfo.systemUptime-started<=1 else {throw RopePhysicsError.invalid("Single global diagnostic exceeded one second")}
            state=old;state.boardHeight += dh*alpha
            for r in state.ropes.indices {
                for i in state.ropes[r].positions.indices {state.ropes[r].positions[i] += corrections[r][i]*alpha}
                for (index,local) in state.ropes[r].attachments {state.ropes[r].positions[index]=state.worldPoint(local)}
            }
            do {
                try RopePassageTopology.refresh(state:&state,input:input)
                guard state.ropes.allSatisfy({$0.positions.allSatisfy({!collider.augmentedContains(state.boardPoint($0))})}) else {throw RopePhysicsError.invalid("Single global trial entered wood")}
                let next=try energy(self)
                trials.append(["trial":trial,"alpha":alpha,"energy":next,"state":AugmentedTrace.points(state)])
                if next<=initialEnergy+1e-18 {accepted=true;break}
            } catch RopePhysicsError.invalid(let reason) {trials.append(["trial":trial,"alpha":alpha,"invalid":reason,"state":AugmentedTrace.points(state)])}
            alpha *= 0.5
        }
        let nextLengths=lengths(self)
        let physical=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[state.boardHeight],channelCache:channelColliderCache)
        let afterMerit=try augmentedMeritParts(state,prediction:prediction,weights:weights,penalty:1)
        let seconds=ProcessInfo.processInfo.systemUptime-started
        let pass=accepted && seconds<=1 && nextLengths["rms"]!*2<=initialLengths["rms"]! && nextLengths["peakStrain"]!*2<=initialLengths["peakStrain"]!
        return ["scope":"one discarded global direction from rejected state, not a step or physical acceptance",
            "variables":size+1,"terms":records.count,"factorizations":1,"solves":1,"seconds":seconds,
            "assemblySeconds":assemblySeconds,"factorSeconds":factorSeconds,"solveSeconds":solveSeconds,
            "linearResidual":residualMax,"directionalDerivative":derivative,"gradient":gradient,"direction":direction,
            "masses":masses,"rows":sparse.map{$0.map{[Double($0.0),$0.1]}},"curvatures":curvatures,"forces":forces,
            "energyBefore":initialEnergy,"acceptedEnergyTrial":accepted,"trials":trials,"beforeLengths":initialLengths,"afterLengths":nextLengths,
            "meritBefore":initialMerit,"meritAfter":afterMerit,"hypothesisPass":pass,
            "physicalDiagnostic":["geometryAccepted":physical.geometryAccepted,"clearance":physical.minimumSegmentClearance,"strain":physical.maximumLocalStrain,"lengthError":physical.totalLengthError,"topology":physical.topologyValid]]
    }
}
