import Foundation

/// This extension is appended only to a fresh native experiment snapshot.
/// Terms share multipliers across every particle block and the height block.
enum AugmentedTrace {
    static var phases:[[String:Any]]=[]
    static var started=0.0
    static func budget() throws {
        guard ProcessInfo.processInfo.systemUptime-started<=1 else {
            throw RopePhysicsError.invalid("Fixed one-second nonlinear candidate budget exhausted")
        }
    }
    static func points(_ state:RopeSimulationState)->[String:Any] {
        ["height":state.boardHeight,"orientation":[state.orientation.vector.x,state.orientation.vector.y,state.orientation.vector.z,state.orientation.vector.w],
         "positions":state.ropes.map{$0.positions.map{[$0.x,$0.y,$0.z]}},
         "crossings":state.ropes.map {rope in rope.portalCrossings.mapValues { ["segment":Double($0.segment),"fraction":$0.fraction] }}]
    }
}

extension RopeDynamicsSolver {
    private enum AugmentedFeature {
        case length(Int,Int)
        case wood(Int,Int,Int,Int) // rope, endpoint A, endpoint B, actual triangle
        case portal(Int,String,Int)
        case selfContact(Int,Int,Int)
        case cord(Int,Int,RopeCordContacts.Contact)
    }
    private struct AugmentedTerm {
        let feature:AugmentedFeature
        let key:String
        let scale:Double
        var dual=0.0
        var startPenalty=0.0
        var penalty=0.0
    }
    private struct AugmentedRow {
        let residual:Double
        let contact:Bool
        let refs:[(Int,Int)]
        let gradients:[SIMD3<Double>]
        let height:Double
    }
    private func augmentedRow(_ feature:AugmentedFeature) throws -> AugmentedRow {
        func row(_ c:Double,_ contact:Bool,_ refs:[(Int,Int)],_ gradients:[SIMD3<Double>],wood:Bool=false)->AugmentedRow {
            var height=0.0
            if wood {height = -gradients.reduce(0.0){$0+$1.y}}
            for k in refs.indices where state.ropes[refs[k].0].attachments[refs[k].1] != nil {height += gradients[k].y}
            return AugmentedRow(residual:c,contact:contact,refs:refs,gradients:gradients,height:height)
        }
        switch feature {
        case .length(let r,let i):
            let rope=state.ropes[r],delta=rope.positions[i+1]-rope.positions[i],length=simd_length(delta)
            guard length>1e-12 else {throw RopePhysicsError.invalid("Collapsed nonlinear material link")}
            let n=delta/length
            return row(length-rope.restLengths[i],false,[(r,i),(r,i+1)],[-n,n])
        case .wood(let r,let i,let j,let triangle):
            let rope=state.ropes[r],a=state.boardPoint(rope.positions[i]),b=state.boardPoint(rope.positions[j])
            let face=collider.mesh.triangles[triangle]
            let hit=try RopeTriangleCollider.augmentedNondegenerateTriangle(a,b,collider.mesh.vertices[face.x],collider.mesh.vertices[face.y],collider.mesh.vertices[face.z])
            let n=state.orientation.act(hit.normal),f=hit.fraction
            return row(hit.distance-rope.radius-RopeRegionGeometry.clearance,true,[(r,i),(r,j)],[n*(1-f),n*f],wood:true)
        case .portal(let r,let id,let edge):
            let rope=state.ropes[r]
            guard let crossing=rope.portalCrossings[id],let portal=portalMap[id] else {throw RopePhysicsError.invalid("Missing nonlinear sliding portal")}
            let i=crossing.segment
            let boundaries=try RopePassageTopology.boundaryConstraints(from:state.boardPoint(rope.positions[i]),to:state.boardPoint(rope.positions[i+1]),portal:portal,radius:rope.radius)
            let boundary=boundaries[edge]
            return row(boundary.residual,true,[(r,i),(r,i+1)],[state.orientation.act(boundary.firstGradient),state.orientation.act(boundary.secondGradient)],wood:true)
        case .selfContact(let r,let i,let j):
            let rope=state.ropes[r],a=rope.positions[i],b=rope.positions[i+1],c=rope.positions[j],d=rope.positions[j+1]
            let pair=RopeTriangleCollider.segmentPair(a,b,c,d),delta=pair.0-pair.1,length=simd_length(delta)
            guard length>1e-10 else {throw RopePhysicsError.invalid("Degenerate nonlinear self-contact")}
            let g=simd_length_squared(d-c)>1e-20 ? min(1,max(0,simd_dot(pair.1-c,d-c)/simd_length_squared(d-c))):0
            var n=length>1e-10 ? delta/length:simd_cross(b-a,d-c)
            n=simd_length(n)>1e-10 ? simd_normalize(n):SIMD3(1,0,0)
            return row(length-2*rope.radius-0.00005,true,[(r,i),(r,i+1),(r,j),(r,j+1)],
                       [n*(1-pair.2),n*pair.2,-n*(1-g),-n*g])
        case .cord(let r,let s,let hit):
            let i=hit.firstSegment,j=hit.secondSegment,first=state.ropes[r],second=state.ropes[s]
            let da=first.positions[i+1]-first.positions[i],db=second.positions[j+1]-second.positions[j]
            let a=first.positions[i]+da*hit.firstLower,b=first.positions[i]+da*hit.firstUpper
            let c=second.positions[j]+db*hit.secondLower,d=second.positions[j]+db*hit.secondUpper
            let pair=RopeTriangleCollider.segmentPair(a,b,c,d),delta=pair.0-pair.1,length=simd_length(delta)
            guard length>1e-10 else {throw RopePhysicsError.invalid("Degenerate nonlinear intercord contact")}
            let localG=simd_length_squared(d-c)>1e-20 ? min(1,max(0,simd_dot(pair.1-c,d-c)/simd_length_squared(d-c))):0
            let f=hit.firstLower+(hit.firstUpper-hit.firstLower)*pair.2,g=hit.secondLower+(hit.secondUpper-hit.secondLower)*localG
            var n=length>1e-10 ? delta/length:simd_cross(b-a,d-c)
            n=simd_length(n)>1e-10 ? simd_normalize(n):SIMD3(1,0,0)
            return row(length-hit.targetDistance,true,[(r,i),(r,i+1),(s,j),(s,j+1)],[n*(1-f),n*f,-n*(1-g),-n*g])
        }
    }

    private mutating func augmentedDiscover(_ terms:inout [AugmentedTerm],_ keys:inout Set<String>,weights:[[Double]]) throws {
        func admit(_ feature:AugmentedFeature,_ key:String,_ scale:Double) throws {
            if keys.contains(key) {return}
            let row=try augmentedRow(feature)
            // Combine repeated references before the global inverse-mass norm.
            var coefficients:[String:SIMD3<Double>]=[:],mass:[String:Double]=[:]
            for k in row.refs.indices {
                let (r,i)=row.refs[k],id="\(r):\(i)"
                if weights[r][i]>0 {coefficients[id,default:.zero] += row.gradients[k];mass[id]=weights[r][i]}
            }
            let response=coefficients.keys.sorted().reduce(row.height*row.height/state.boardMass){$0+simd_length_squared(coefficients[$1]!)*mass[$1]!}
            guard response.isFinite,response>=0 else {throw RopePhysicsError.invalid("Invalid shared effective mass")}
            if response==0 {
                guard row.contact ? row.residual>=(-1e-8):abs(row.residual)<=1e-8 else {throw RopePhysicsError.invalid("Unsatisfied zero-response nonlinear constraint")}
                return
            }
            let initial=1/response
            terms.append(AugmentedTerm(feature:feature,key:key,scale:scale,startPenalty:initial,penalty:min(1e8,initial)))
            keys.insert(key)
        }
        for (r,rope) in state.ropes.enumerated() {
            for i in rope.restLengths.indices {try admit(.length(r,i),"length:\(r):\(i)",rope.restLengths[i])}
            for i in rope.positions.indices {
                try AugmentedTrace.budget()
                let a=state.boardPoint(rope.positions[i])
                guard !collider.augmentedContains(a) else {throw RopePhysicsError.invalid("Nonlinear centerline entered wood")}
                for hit in collider.segmentContacts(from:a,to:a,radius:rope.radius+RopeRegionGeometry.clearance+0.00005) {
                    guard let face=hit.triangleIndex else {throw RopePhysicsError.invalid("Contact has no triangle authority")}
                    try admit(.wood(r,i,i,face),"point:\(r):\(i):\(face)",rope.radius)
                }
                if i<rope.restLengths.count {
                    let b=state.boardPoint(rope.positions[i+1])
                    for hit in collider.segmentContacts(from:a,to:b,radius:rope.radius+RopeRegionGeometry.clearance+0.00005) where hit.fraction>1e-6 && hit.fraction<1-1e-6 {
                        guard let face=hit.triangleIndex else {throw RopePhysicsError.invalid("Whole-link contact has no triangle authority")}
                        try admit(.wood(r,i,i+1,face),"link:\(r):\(i):\(face)",rope.radius)
                    }
                }
            }
            for id in rope.portalCrossings.keys.sorted() {
                guard let portal=portalMap[id] else {throw RopePhysicsError.invalid("Missing discovery portal")}
                // All original aperture half-spaces: no row omitted on a later crossing segment.
                for edge in portal.boundary.indices {try admit(.portal(r,id,edge),"portal:\(r):\(id):\(edge)",rope.radius)}
            }
            for pair in RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths) {
                try admit(.selfContact(r,pair.x,pair.y),"self:\(r):\(pair.x):\(pair.y)",2*rope.radius)
            }
        }
        for r in state.ropes.indices {for s in state.ropes.indices where s>r {
            for hit in RopeCordContacts.between(state.ropes[r],state.ropes[s],margin:0.0001) {
                let key="cord:\(r):\(s):\(hit.firstSegment):\(hit.secondSegment):\(hit.firstLower.bitPattern):\(hit.firstUpper.bitPattern):\(hit.secondLower.bitPattern):\(hit.secondUpper.bitPattern):\(hit.targetDistance.bitPattern)"
                try admit(.cord(r,s,hit),key,state.ropes[r].radius+state.ropes[s].radius)
            }
        }}
    }

    private func augmentedMeritParts(_ candidate:RopeSimulationState,prediction:RopeSimulationState,weights:[[Double]],penalty:Double) throws -> [String:Double] {
        var objective=0.5*state.boardMass*pow(candidate.boardHeight-prediction.boardHeight,2)
        var length=0.0,wood=0.0,selfContact=0.0,portal=0.0,cord=0.0
        for (r,rope) in candidate.ropes.enumerated() {
            for i in rope.positions.indices where weights[r][i]>0 {objective += 0.5*simd_length_squared(rope.positions[i]-prediction.ropes[r].positions[i])/weights[r][i]}
            for i in rope.restLengths.indices {
                length += abs(simd_distance(rope.positions[i],rope.positions[i+1])-rope.restLengths[i])
                let hits=collider.segmentContacts(from:candidate.boardPoint(rope.positions[i]),to:candidate.boardPoint(rope.positions[i+1]),radius:rope.radius+RopeRegionGeometry.clearance)
                wood += max(0,(hits.map{$0.penetrationDepth}.max() ?? 0)-Self.contactLinearTolerance)
            }
            for pair in RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths) {
                let points=RopeTriangleCollider.segmentPair(rope.positions[pair.x],rope.positions[pair.x+1],rope.positions[pair.y],rope.positions[pair.y+1])
                selfContact += max(0,2*rope.radius+0.00005-simd_distance(points.0,points.1)-Self.contactLinearTolerance)
            }
            for id in rope.portalCrossings.keys.sorted() {
                let crossing=rope.portalCrossings[id]!
                guard let region=portalMap[id] else {throw RopePhysicsError.invalid("Missing diagnostic portal")}
                let margin=RopePassageTopology.boundaryMargin(candidate.boardPoint(crossing.point(in:rope.positions)),portal:region)
                portal += max(0,rope.radius+RopeRegionGeometry.clearance-margin-Self.contactLinearTolerance)
            }
        }
        for r in candidate.ropes.indices {for s in candidate.ropes.indices where s>r {
            for hit in RopeCordContacts.between(candidate.ropes[r],candidate.ropes[s],margin:0.0001) {cord += max(0,hit.targetDistance-hit.distance-Self.contactLinearTolerance)}
        }}
        return ["inertia":objective,"length":length,"wood":wood,"self":selfContact,"portal":portal,"intercord":cord,"penalty":penalty,"total":objective+penalty*(length+wood+selfContact+portal+cord)]
    }

    private mutating func augmentedCorrect(prediction:RopeSimulationState) throws {
        let initial=state
        let weights=state.ropes.map {rope in rope.positions.indices.map {i -> Double in
            if rope.supports[i] != nil || rope.attachments[i] != nil {return 0}
            let length=(i>0 ? rope.restLengths[i-1]:0)+(i<rope.restLengths.count ? rope.restLengths[i]:0)
            return 2/(rope.linearMass*length)
        }}
        var blocks:[(Int,Int)]=[]
        for r in state.ropes.indices {for i in state.ropes[r].positions.indices where weights[r][i]>0 {blocks.append((r,i))}}
        blocks.append((-1,-1)) // One globally shared board-height block, never one per rope.
        var terms:[AugmentedTerm]=[],keys:Set<String>=[]
        var lastMovement=Double.infinity
        var completedLocals:[[String:Any]]=[]
        var inFlight:[String:Any]=[:]
        defer {
            let partial=terms.map {term -> [String:Any] in
                var entry:[String:Any]=["key":term.key,"lambda":term.dual,"rho":term.penalty]
                if let row=try? augmentedRow(term.feature) {entry["C"]=row.residual;entry["contact"]=row.contact}
                return entry
            }
            AugmentedTrace.phases.append(["phase":"return-or-rejection","state":AugmentedTrace.points(state),"terms":partial,"locals":completedLocals,"inFlight":inFlight])
        }
        AugmentedTrace.phases.append(["phase":"prediction","state":AugmentedTrace.points(state)])
        for sweep in 0..<16 {
            try AugmentedTrace.budget()
            try augmentedDiscover(&terms,&keys,weights:weights)
            var incidence=Array(repeating:[Int](),count:blocks.count)
            let blockIDs=Dictionary(uniqueKeysWithValues:blocks.enumerated().map{("\($0.element.0):\($0.element.1)",$0.offset)})
            for index in terms.indices {
                let row=try augmentedRow(terms[index].feature)
                var ids:Set<Int>=[]
                for ref in row.refs {if let id=blockIDs["\(ref.0):\(ref.1)"] {ids.insert(id)}}
                // A portal's crossing may migrate to a neighboring material link.
                if case .portal(let r,_,_) = terms[index].feature {for id in blocks.indices where blocks[id].0==r {ids.insert(id)}}
                if row.height != 0 || row.refs.contains(where:{state.ropes[$0.0].attachments[$0.1] != nil}) {ids.insert(blocks.count-1)}
                // Wood/portals depend explicitly on board height even when its
                // instantaneous derivative happens to vanish.
                switch terms[index].feature {case .wood,.portal:ids.insert(blocks.count-1);default:break}
                for id in ids {incidence[id].append(index)}
            }
            let beforeSweep=state
            var localTrials:[[String:Any]]=[]
            completedLocals=[]
            for block in blocks.indices {
                try AugmentedTrace.budget()
                let (r,i)=blocks[block],height=r<0
                let masses=height ? [state.boardMass]:Array(repeating:1/weights[r][i],count:3)
                let offset=height ? [state.boardHeight-prediction.boardHeight]:[
                    state.ropes[r].positions[i].x-prediction.ropes[r].positions[i].x,
                    state.ropes[r].positions[i].y-prediction.ropes[r].positions[i].y,
                    state.ropes[r].positions[i].z-prediction.ropes[r].positions[i].z]
                let ids=incidence[block],rows=try ids.map{try augmentedRow(terms[$0].feature)}
                let gradients=rows.map {row -> [Double] in
                    if height {return [row.height]}
                    var gradient=SIMD3<Double>.zero
                    for k in row.refs.indices where row.refs[k].0==r && row.refs[k].1==i {gradient += row.gradients[k]}
                    return [gradient.x,gradient.y,gradient.z]
                }
                let direction=try NonlinearAugmented.direction(masses:masses,offset:offset,gradients:gradients,
                    residuals:rows.map{$0.residual},duals:ids.map{terms[$0].dual},penalties:ids.map{terms[$0].penalty},contacts:rows.map{$0.contact})
                var corrections=state.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
                let dh=height ? direction[0]:0
                if !height {corrections[r][i]=SIMD3(direction[0],direction[1],direction[2])}
                var alpha=Self.correctionFraction(ropes:state.ropes,corrections:corrections,heightCorrection:dh)
                func energy(_ solver:RopeDynamicsSolver) throws -> Double {
                    let currentOffset=height ? [solver.state.boardHeight-prediction.boardHeight]:[
                        solver.state.ropes[r].positions[i].x-prediction.ropes[r].positions[i].x,
                        solver.state.ropes[r].positions[i].y-prediction.ropes[r].positions[i].y,
                        solver.state.ropes[r].positions[i].z-prediction.ropes[r].positions[i].z]
                    var value=zip(masses,currentOffset).reduce(0.0){$0+0.5*$1.0*$1.1*$1.1}
                    for id in ids {
                        let row=try solver.augmentedRow(terms[id].feature)
                        value += try NonlinearAugmented.energy(row.residual,dual:terms[id].dual,penalty:terms[id].penalty,contact:row.contact)
                    }
                    // Moving height also moves attached particles; their inertia
                    // is absent from the original free-particle objective.
                    return value
                }
                let old=state,score=try energy(self)
                var accepted=false,trialScores:[[String:Any]]=[]
                inFlight=["block":block,"rope":r,"particle":i,"direction":direction,"oldEnergy":score,"origin":height ? [old.boardHeight]:[old.ropes[r].positions[i].x,old.ropes[r].positions[i].y,old.ropes[r].positions[i].z]]
                for trial in 0..<16 {
                    try AugmentedTrace.budget()
                    state=old;state.boardHeight += dh*alpha
                    if !height {state.ropes[r].positions[i] += corrections[r][i]*alpha}
                    for rr in state.ropes.indices {for (index,local) in state.ropes[rr].attachments {state.ropes[rr].positions[index]=state.worldPoint(local)}}
                    do {
                        try RopePassageTopology.refresh(state:&state,input:input)
                        let refs=height ? state.ropes.flatMap{$0.positions.map{state.boardPoint($0)}}:[state.boardPoint(state.ropes[r].positions[i])]
                        guard refs.allSatisfy({!collider.augmentedContains($0)}) else {throw RopePhysicsError.invalid("Local trial entered wood")}
                        let next=try energy(self)
                        trialScores.append(["trial":trial,"alpha":alpha,"energy":next])
                        inFlight["trials"]=trialScores
                        if next<=score+1e-18 {accepted=true;break}
                    } catch RopePhysicsError.invalid(let reason) {trialScores.append(["trial":trial,"alpha":alpha,"invalid":reason]);inFlight["trials"]=trialScores}
                    alpha *= 0.5
                }
                inFlight["accepted"]=accepted
                localTrials.append(inFlight)
                inFlight=[:]
                completedLocals=localTrials
                if !accepted {
                    let rejected=state;state=old
                    AugmentedTrace.phases.append(["phase":"local-rejection","sweep":sweep,"locals":localTrials,"state":AugmentedTrace.points(rejected)])
                    throw RopePhysicsError.invalid("Fixed local augmented line search exhausted")
                }
            }
            lastMovement=abs(state.boardHeight-beforeSweep.boardHeight)
            for r in state.ropes.indices {for i in state.ropes[r].positions.indices {lastMovement=max(lastMovement,simd_distance(state.ropes[r].positions[i],beforeSweep.ropes[r].positions[i]))}}
            var termTrace:[[String:Any]]=[]
            for index in terms.indices {
                let row=try augmentedRow(terms[index].feature),oldPenalty=terms[index].penalty,oldDual=terms[index].dual
                terms[index].dual=try NonlinearAugmented.force(row.residual,dual:oldDual,penalty:oldPenalty,contact:row.contact)
                terms[index].penalty=min(1e8,oldPenalty+10*terms[index].startPenalty*abs(row.residual)/terms[index].scale)
                termTrace.append(["key":terms[index].key,"C":row.residual,"lambdaBefore":oldDual,"lambda":terms[index].dual,"rhoBefore":oldPenalty,"rho":terms[index].penalty])
            }
            AugmentedTrace.phases.append(["phase":"sweep","sweep":sweep,"movement":lastMovement,"strain":maximumStrain(),"state":AugmentedTrace.points(state),"terms":termTrace,"locals":localTrials])
        }
        try augmentedDiscover(&terms,&keys,weights:weights)
        var gradient=state.ropes.enumerated().map {r,rope in rope.positions.indices.map {i in weights[r][i]>0 ? (rope.positions[i]-prediction.ropes[r].positions[i])/weights[r][i]:.zero}}
        var heightGradient=state.boardMass*(state.boardHeight-prediction.boardHeight)
        var equality=0.0,minC=0.0,minGap=0.0,complementarity=0.0,maxCompression=0.0
        var finalTerms:[[String:Any]]=[]
        for term in terms {
            let row=try augmentedRow(term.feature),gap=row.residual-NonlinearAugmented.epsilon*term.dual
            for k in row.refs.indices {let (r,i)=row.refs[k];if weights[r][i]>0 {gradient[r][i] += row.gradients[k]*term.dual}}
            heightGradient += row.height*term.dual
            if row.contact {minC=min(minC,row.residual);minGap=min(minGap,gap);complementarity=max(complementarity,abs(term.dual*gap));maxCompression=max(maxCompression,term.dual)}
            else {equality=max(equality,abs(gap))}
            finalTerms.append(["key":term.key,"C":row.residual,"lambda":term.dual,"rho":term.penalty,"gap":gap,
                "contact":row.contact,"references":row.refs.map{[$0.0,$0.1]},"gradients":row.gradients.map{[$0.x,$0.y,$0.z]},"heightGradient":row.height])
        }
        let stationarity=max(abs(heightGradient),gradient.flatMap{$0}.flatMap{[$0.x,$0.y,$0.z]}.map{abs($0)}.max() ?? 0)
        let penalty=max(1,2*(terms.map{abs($0.dual)}.max() ?? 0))
        let before=try augmentedMeritParts(initial,prediction:prediction,weights:weights,penalty:penalty)
        let after=try augmentedMeritParts(state,prediction:prediction,weights:weights,penalty:penalty)
        let exactBefore=try merit(initial,prediction:prediction,weights:weights,penalty:penalty)
        let exactAfter=try merit(state,prediction:prediction,weights:weights,penalty:penalty)
        guard abs(exactBefore-before["total"]!)<=1e-18,abs(exactAfter-after["total"]!)<=1e-18 else {throw RopePhysicsError.invalid("Merit component reconstruction differs")}
        let certificate=stationarity<=1e-10 && equality<=1e-8 && minC>=(-1e-8) && minGap>=(-1e-10) && maxCompression<=0 && complementarity<=1e-14
        let physical=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:[state.boardHeight],channelCache:channelColliderCache)
        AugmentedTrace.phases.append(["phase":"final","state":AugmentedTrace.points(state),"terms":finalTerms,
            "stationarity":stationarity,"equality":equality,"minC":minC,"minGap":minGap,"complementarity":complementarity,
            "maxCompression":maxCompression,"certificate":certificate,"meritBefore":before,"meritAfter":after,
            "movement":lastMovement,"strain":maximumStrain(),"physicalDiagnostic":["geometryAccepted":physical.geometryAccepted,
                "strain":physical.maximumLocalStrain,"lengthError":physical.totalLengthError,"clearance":physical.minimumSegmentClearance,"topology":physical.topologyValid],
            "proposalCheckpoint":foundationCheckpoint()])
        guard certificate,maximumStrain()<0.0002,lastMovement<1e-8,exactAfter<=exactBefore+1e-18 else {
            throw RopePhysicsError.invalid("Fixed nonlinear augmented final certificate/convergence/merit rejected")
        }
        try AugmentedTrace.budget()
        for term in terms {if case .length(let r,let i)=term.feature {distanceTension[r][i]=max(0,term.dual)}}
    }
}
