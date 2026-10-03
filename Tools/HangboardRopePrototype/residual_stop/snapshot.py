from pathlib import Path

def contact_source(text):
    needle='        let activeIDs: [Int]\n'
    assert text.count(needle)==1
    text=text.replace(needle,needle+'        var residualOperator:ResidualOperator?=nil\n')
    needle='multipliers:multipliers,activeIDs:active)'
    assert text.count(needle)==1
    text=text.replace(needle,'multipliers:multipliers,activeIDs:active,residualOperator:ResidualOperator(factor:factor,rows:active.map{contacts[$0]},responses:try active.map{try response($0)},lower:cholesky.lower))')
    return text+'\n'+(Path(__file__).parent/'Operator.swift').read_text()

def collider_source(text):
    text=text.replace('    var timeOfImpact: Double? = nil','    var sourceFeature:SIMD2<Int>?=nil\n    var timeOfImpact: Double? = nil')
    start=text.index('    private static func triangleClosest(')
    end=text.index('\n    static func segmentPair(',start)
    method=text[start:end].replace('private static func triangleClosest(', 'private static func triangleClosestSource(').replace('-> SIMD3<Double> {','-> (SIMD3<Double>,Int) {')
    replacements=[('return a }','return (a,0) }'),('return b }','return (b,1) }'),
        ('return a+ab*(d1/(d1-d3)) }','return (a+ab*(d1/(d1-d3)),2) }'),('return c }','return (c,3) }'),
        ('return a+ac*(d2/(d2-d6)) }','return (a+ac*(d2/(d2-d6)),4) }'),
        ('return b+(c-b)*((d4-d3)/((d4-d3)+(d5-d6))) }','return (b+(c-b)*((d4-d3)/((d4-d3)+(d5-d6))),5) }'),
        ('return a+ab*(vb*inverse)+ac*(vc*inverse)','return (a+ab*(vb*inverse)+ac*(vc*inverse),6)')]
    for a,b in replacements:
        assert a in method,a
        method=method.replace(a,b)
    s=text.index('    static func segmentPair(')
    e=text.index('\n}\n',s)
    pair=text[s:e].replace('func segmentPair(', 'func segmentPairSource(').replace('-> (SIMD3<Double>,SIMD3<Double>,Double) {','-> (SIMD3<Double>,SIMD3<Double>,Double,Int) {')
    pair=pair.replace('return (p+d1*s,a+d2*t,s)', 'return (p+d1*s,a+d2*t,s,(s==0 ? 0:s==1 ? 1:2)+3*(t==0 ? 0:t==1 ? 1:2)+9*(aa<=1e-24 ? 1:ee<=1e-24 ? 2:aa*ee-simd_dot(d1,d2)*simd_dot(d1,d2)<=1e-24 ? 3:0))')
    text=text[:e]+'\n'+method+'\n'+pair+text[e:]
    s=text.index('    func fusedContactEvaluation(');e=text.index('    private struct FusedWitness',s)
    fused=text[s:e]
    fused=fused.replace('faceNormal:normal)', 'faceNormal:normal,faceIndex:index)')
    fused=fused.replace('let q=Self.triangleClosest(start,a,b,c)', 'let (q,branch)=Self.triangleClosestSource(start,a,b,c)')
    fused=fused.replace('let q=Self.triangleClosest(end,a,b,c)', 'let (q,branch)=Self.triangleClosestSource(end,a,b,c)')
    for receiver in ['first','row','merit']:
        fused=fused.replace(receiver+'.consider(start,q,0)',receiver+'.consider(start,q,0,source:100+branch)')
    for receiver in ['row','merit']:
        fused=fused.replace(receiver+'.consider(end,q,1)',receiver+'.consider(end,q,1,source:200+branch)')
        fused=fused.replace(receiver+'.consider(p,p,t)',receiver+'.consider(p,p,t,source:300)')
        fused=fused.replace(receiver+'.consider(q.0,q.1,q.2)',receiver+'.consider(q.0,q.1,q.2,source:400+edgeID*100+q.3)')
    fused=fused.replace('last.consider(end,q,0)','last.consider(end,q,0,source:100+branch)')
    fused=fused.replace('Self.segmentPair(', 'Self.segmentPairSource(')
    fused=fused.replace('for q in [ab,bc,ca]', 'for (edgeID,q) in [ab,bc,ca].enumerated()')
    text=text[:s]+fused+text[e:]
    text=text.replace('        let faceNormal:SIMD3<Double>\n','        let faceNormal:SIMD3<Double>\n        let faceIndex:Int\n')
    text=text.replace('mutating func consider(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ fraction:Double) {','mutating func consider(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ fraction:Double,source:Int) {')
    text=text.replace('fraction:fraction,penetrationDepth:radius-distance)\n        }','fraction:fraction,penetrationDepth:radius-distance,sourceFeature:SIMD2(faceIndex,source))\n        }')
    return text

def solver_source(text):
    text=text.replace('    private var cachedEvaluation:RopeConfigurationEvaluation?','    private var residualContext:ResidualContext?\n    private var cachedEvaluation:RopeConfigurationEvaluation?')
    text=text.replace('        var secondRope:Int?=nil','        var sourceID:String?=nil\n        var secondRope:Int?=nil')
    s=text.index('        let evaluation=configurationEvaluation(state)',text.index('    private mutating func correctConstraints('))
    e=text.index('        let solved=try contactCorrection',s)
    builder=text[s:e]
    builder=builder.replace('contact:true,lengthSegment:nil))', 'contact:true,lengthSegment:nil,sourceID:hit.sourceFeature.map{"wood-point/\\(r)/\\(i)/\\($0.x)/\\($0.y)"}))',1)
    builder=builder.replace('contact:false,lengthSegment:i))','contact:false,lengthSegment:i,sourceID:"length/\\(r)/\\(i)"))')
    builder=builder.replace('residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))','residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil,sourceID:hit.sourceFeature.map{"wood-link/\\(r)/\\(i)/\\($0.x)/\\($0.y)"}))')
    builder=builder.replace('for boundary in boundaries where','for (boundaryIndex,boundary) in boundaries.enumerated() where')
    builder=builder.replace('residual:boundary.residual,contact:true,lengthSegment:nil))','residual:boundary.residual,contact:true,lengthSegment:nil,sourceID:"portal/\\(r)/\\(id)/\\(i)/\\(boundaryIndex)/\\(crossing.fraction==0 ? 0:crossing.fraction==1 ? 1:2)"))')
    builder=builder.replace('RopeTriangleCollider.segmentPair(rope.positions[i]','RopeTriangleCollider.segmentPairSource(rope.positions[i]')
    builder=builder.replace('residual:distance-2*rope.radius-0.00005,contact:true,lengthSegment:nil))','residual:distance-2*rope.radius-0.00005,contact:true,lengthSegment:nil,sourceID:distance>1e-10 ? "self/\\(r)/\\(i)/\\(j)/\\(witness.3)":nil))')
    text=text[:s]+'        let (rows,weights)=try buildConstraintRows(prediction:prediction)\n'+text[e:]
    text+='\nextension RopeDynamicsSolver {\n    private mutating func buildConstraintRows(prediction:RopeSimulationState) throws -> ([ConstraintRow],[[Double]]) {\n'+builder+'        return (rows,weights)\n    }\n}\n'
    needle='        contactHints=solved.activeIDs.map{(contacts[$0],solved.multipliers[$0])}'
    text=text.replace(needle,'''        residualContext=nil
        if let op=solved.residualOperator,op.factor.borderCount==1 {
            var raw=Array(repeating:0.0,count:rows.count)
            for (k,id) in equalityIDs.enumerated() {raw[id]=solved.base[backbone.rowVariables[k]!]}
            for k in contactIDs.indices {raw[contactIDs[k]]=solved.multipliers[k]}
            residualContext=ResidualContext(factor:op,variables:variables,equalityIDs:equalityIDs,rowVariables:backbone.rowVariables,
                activeIDs:solved.activeIDs.map{contactIDs[$0]},multipliers:raw,rows:rows)
        }
'''+needle)
    needle='                    return (convergenceExperiment ? 1:alpha)*max(maximum,abs(heightCorrection))'
    assert text.count(needle)==1
    text=text.replace(needle,'''                    if ResidualStopTrace.enabled && convergenceExperiment && alpha==1,
                       let estimate=postStepResidual(prediction:prediction) {
                        let arrived=abs(simd_dot(state.orientation.vector,residualTarget.vector))>1-1e-12
                        let limit=arrived ? 0.001*residualDt:0.00005
                        if maximumStrain()<0.0002 && estimate<limit {ResidualStopTrace.stops += 1;return estimate}
                    }
'''+needle)
    text=text.replace('    private var residualContext:ResidualContext?', '    private var residualTarget=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))\n    private var residualDt=1.0/240\n    private var residualContext:ResidualContext?')
    needle='        let old=state\n'
    assert text.count(needle)==1
    text=text.replace(needle,'        residualTarget=targetOrientation;residualDt=dt\n'+needle)
    return text+'\n'+(Path(__file__).parent/'Stop.swift').read_text()
