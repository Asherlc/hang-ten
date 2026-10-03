"""Differentiate the existing outside-wood and sliding-portal merit terms."""
from .snapshot import solver_source as guarded_source, once

def collider_source(source):
    source=once(source,'    var timeOfImpact: Double? = nil',
        '    var timeOfImpact: Double? = nil\n    var armijoWitnessUnique:Bool=false\n    var armijoDerivativeWitnesses:[RopeArmijoDerivativeWitness]=[]')
    source+='\nstruct RopeArmijoDerivativeWitness:Sendable {let fraction:Double;let normal:SIMD3<Double>}\n'
    assert source.count('FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)')==3
    source=source.replace('FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)',
        'FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal,armijoTrackDerivative:false)')
    source=once(source,'FusedWitness(best:meritSquare,radius:meritRadius,faceNormal:normal)',
        'FusedWitness(best:meritSquare,radius:meritRadius,faceNormal:normal,armijoTrackDerivative:true)')
    beginning,tail=source.split('    private struct FusedWitness {',1)
    tail=once(tail,'        let faceNormal:SIMD3<Double>','        let faceNormal:SIMD3<Double>\n        let armijoTrackDerivative:Bool')
    tail=once(tail,'            guard distanceSquared<best else{return}', '''            if armijoTrackDerivative,distanceSquared==best,let previous=hit {
                if previous.fraction != fraction || previous.centerlinePoint != p || previous.surfacePoint != q {
                    hit?.armijoWitnessUnique=false
                }
                let distance=sqrt(distanceSquared)
                let normal=distance>1e-10 ? (p-q)/distance:faceNormal
                if !previous.armijoDerivativeWitnesses.contains(where:{$0.fraction==fraction && $0.normal==normal}) {
                    hit?.armijoDerivativeWitnesses.append(RopeArmijoDerivativeWitness(fraction:fraction,normal:normal))
                }
            }
            guard distanceSquared<best else{return}''')
    tail=once(tail,'fraction:fraction,penetrationDepth:radius-distance)',
                  'fraction:fraction,penetrationDepth:radius-distance,armijoWitnessUnique:true)')
    tail=once(tail,'armijoWitnessUnique:true)\n        }', '''armijoWitnessUnique:true)
            if armijoTrackDerivative {
                let primaryNormal=hit!.normal
                hit?.armijoDerivativeWitnesses=[RopeArmijoDerivativeWitness(fraction:fraction,normal:primaryNormal)]
            }
        }''')
    tail=once(tail,'            if hit.penetrationDepth>result[duplicate].penetrationDepth {result[duplicate]=hit}',
              '''            if hit.penetrationDepth>result[duplicate].penetrationDepth {result[duplicate]=hit}
            else if hit.penetrationDepth==result[duplicate].penetrationDepth {
                let old=result[duplicate]
                result[duplicate].armijoWitnessUnique=old.armijoWitnessUnique && hit.armijoWitnessUnique &&
                    old.fraction==hit.fraction && old.centerlinePoint==hit.centerlinePoint && old.surfacePoint==hit.surfacePoint
                for witness in hit.armijoDerivativeWitnesses where !result[duplicate].armijoDerivativeWitnesses.contains(where:{$0.fraction==witness.fraction && $0.normal==witness.normal}) {
                    result[duplicate].armijoDerivativeWitnesses.append(witness)
                }
            }''')
    return beginning+'    private struct FusedWitness {'+tail

def solver_source(source):
    source=guarded_source(source)
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var verifyArmijoDerivative=false')
    source=once(source,'        var armijoRejected=0,originalRejected=0',
                '''        let derivativeCheck=verifyArmijoDerivative && armijoSlope != nil ? try verifyArmijoSlope(
            before:state,prediction:prediction,weights:weights,corrections:corrections,height:heightCorrection,
            penalty:penalty,score:score,slope:armijoSlope!):[]
        var armijoRejected=0,originalRejected=0''')
    source=once(source,'"armijoRejected":armijoRejected,"originalRejected":originalRejected]',
                '"armijoRejected":armijoRejected,"originalRejected":originalRejected,"derivativeCheck":derivativeCheck]')
    start=source.index('        for (r,rope) in state.ropes.enumerated() {',source.index('private func armijoDirectionalDerivative'))
    end=source.index('        var objective=',start)
    source=source[:start]+'''        guard evaluation.clearances.allSatisfy({$0.allSatisfy{$0 != nil}}) else {return nil}
        var contactDerivative=0.0
        for (r,rope) in state.ropes.enumerated() {
            for i in rope.restLengths.indices {
                let hits=evaluation.merits[r][i]
                guard let maximum=hits.map({$0.penetrationDepth}).max() else {continue}
                let argument=maximum-Self.contactLinearTolerance
                if argument<0 {continue}
                let a=RopeArmijo.displacement(rope,i,corrections[r][i],height)
                let b=RopeArmijo.displacement(rope,i+1,corrections[r][i+1],height)
                var rates:[Double]=[]
                for hit in hits where hit.penetrationDepth==maximum {
                    guard !hit.armijoDerivativeWitnesses.isEmpty,simd_distance(hit.centerlinePoint,hit.surfacePoint)>1e-10 else {return nil}
                    for witness in hit.armijoDerivativeWitnesses {
                        let displacement=a*(1-witness.fraction)+b*witness.fraction-SIMD3<Double>(0,height,0)
                        rates.append(-simd_dot(state.orientation.act(witness.normal),displacement))
                    }
                }
                contactDerivative += RopeArmijo.hingeSlope(argument:argument,rate:rates.max()!)
            }
            for (id,crossing) in rope.portalCrossings {
                guard let portal=portalMap[id],crossing.fraction>1e-8,crossing.fraction<1-1e-8 else {return nil}
                let i=crossing.segment,a=state.boardPoint(rope.positions[i]),b=state.boardPoint(rope.positions[i+1])
                let point=state.boardPoint(crossing.point(in:rope.positions))
                let margins=portal.boundary.indices.map {j -> Double in
                    let start=portal.boundary[j],end=portal.boundary[(j+1)%portal.boundary.count]
                    var inward=simd_normalize(simd_cross(portal.normal,end-start))
                    if simd_dot(inward,portal.center-start)<0 {inward = -inward}
                    return simd_dot(point-start,inward)
                }
                let minimum=margins.min()!,argument=rope.radius+RopeRegionGeometry.clearance-minimum-Self.contactLinearTolerance
                if argument<0 {continue}
                guard let boundaries=try? RopePassageTopology.boundaryConstraints(from:a,to:b,portal:portal,radius:rope.radius) else {return nil}
                let da=state.orientation.inverse.act(RopeArmijo.displacement(rope,i,corrections[r][i],height)-SIMD3<Double>(0,height,0))
                let db=state.orientation.inverse.act(RopeArmijo.displacement(rope,i+1,corrections[r][i+1],height)-SIMD3<Double>(0,height,0))
                let rates=margins.indices.filter{margins[$0]==minimum}.map {j in
                    -simd_dot(boundaries[j].firstGradient,da)-simd_dot(boundaries[j].secondGradient,db)
                }
                contactDerivative += RopeArmijo.hingeSlope(argument:argument,rate:rates.max()!)
            }
        }
'''+source[end:]
    source=once(source,'let slope=objective+penalty*violation','let slope=objective+penalty*(violation+contactDerivative)')
    source+='''
extension RopeDynamicsSolver {
    private mutating func verifyArmijoSlope(before:RopeSimulationState,prediction:RopeSimulationState,weights:[[Double]],
        corrections:[[SIMD3<Double>]],height:Double,penalty:Double,score:Double,slope:Double) throws -> [[String:Double]] {
        let saved=cachedEvaluation
        defer {cachedEvaluation=saved}
        var checks:[[String:Double]]=[]
        for h in [1e-3,1e-4,1e-5] {
            var trial=before;trial.boardHeight += height*h
            for r in trial.ropes.indices {
                for i in trial.ropes[r].positions.indices {trial.ropes[r].positions[i] += corrections[r][i]*h}
                for (i,local) in trial.ropes[r].attachments {trial.ropes[r].positions[i]=trial.worldPoint(local)}
            }
            try RopePassageTopology.refresh(state:&trial,input:input)
            let value=try merit(trial,prediction:prediction,weights:weights,penalty:penalty)
            let numerical=(value-score)/h
            checks.append(["alpha":h,"analytic":slope,"numerical":numerical,"error":abs(numerical-slope)])
        }
        guard checks.last!["error"]!<=1e-8 else {throw RopePhysicsError.invalid("full merit derivative oracle")}
        return checks
    }
}
'''
    return source
