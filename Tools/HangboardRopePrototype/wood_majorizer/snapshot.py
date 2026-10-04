"""Native-only rank-one moving-rope-fraction PSD majorizer."""
from pathlib import Path
from armijo.snapshot import once
from arrival_stop.snapshot import driver_source as arrival_driver

def collider_source(source):
    source=once(source,'    var timeOfImpact: Double? = nil','    var timeOfImpact: Double? = nil\n    var woodFaceIndex:Int?=nil')
    start=source.index('    private struct FusedWitness {')
    finish=source.index('    private static func mergeFused',start)
    piece=source[start:finish]
    piece=once(piece,'        let faceNormal:SIMD3<Double>','        let faceNormal:SIMD3<Double>\n        let faceIndex:Int')
    piece=once(piece,'penetrationDepth:radius-distance)','penetrationDepth:radius-distance,woodFaceIndex:faceIndex)')
    source=source[:start]+piece+source[finish:]
    assert source.count('faceNormal:normal)')==4
    source=source.replace('faceNormal:normal)','faceNormal:normal,faceIndex:index)')
    return source+'\n'+Path(__file__).with_name('Selection.swift.txt').read_text()

def solver_source(source):
    source=once(source,'    var armijoExperiment=false',"""    var armijoExperiment=false
    var woodMajorizerExperiment=false
    private struct WoodTerm {let rope:Int,first:Int;let vector:[Double];let scale:Double}
    private var woodTerms:[WoodTerm]=[]""")
    source=once(source,'        var secondRope:Int?=nil','        var secondRope:Int?=nil\n        var woodHit:RopeSegmentContact?=nil')
    if 'var sourceID:String?' in source:
        old='sourceID:hit.sourceFeature.map{"wood-link/\\(r)/\\(i)/\\($0.x)/\\($0.y)"}))'
        source=once(source,old,old[:-2]+',woodHit:hit))')
    else:
        source=once(source,'residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil))\n                }\n            }',
            'residual:0.00005-hit.penetrationDepth,contact:true,lengthSegment:nil,woodHit:hit))\n                }\n            }')
    # The identical equality layout is prepared before hints; numeric factor only once, after H terms.
    start=source.index('        let borderRows=rows.indices.filter',source.index('    private func constraintBackbone'))
    end=source.index('        var bandwidth=0',start)
    layout=source[start:end]
    source=source[:start]+"""        let layout=constraintLayout(rows:rows,weights:weights)
        let borderRows=layout.borderRows,local=layout.local,variables=layout.variables,rowVariables=layout.rowVariables,size=layout.size
"""+source[end:]
    pos=source.index('    private func constraintBackbone')
    helper="""    private func constraintLayout(rows:[ConstraintRow],weights:[[Double]])
        ->(borderRows:[Int],local:[Int],variables:[[SIMD3<Int>]],rowVariables:[Int:Int],size:Int) {
"""+layout+"""        return (borderRows,local,variables,rowVariables,size)
    }

"""
    source=source[:pos]+helper+source[pos:]
    source=once(source,'        let backbone=try constraintBackbone(rows:equalityIDs.map{rows[$0]},weights:weights,prediction:prediction)\n        let variables=backbone.variables',
        '''        woodTerms=[]
        let originalBackbone = woodMajorizerExperiment ? nil : (try constraintBackbone(rows:equalityIDs.map{rows[$0]},weights:weights,prediction:prediction))
        let variables=originalBackbone?.variables ?? constraintLayout(rows:equalityIDs.map{rows[$0]},weights:weights).variables''')
    source=once(source,'        let fallbackSolver=self',"""        woodTerms=woodMajorizerExperiment ? buildWoodTerms(rows:rows,weights:weights,contactIDs:contactIDs,initial:initial):[]
        let backbone=try originalBackbone ?? constraintBackbone(rows:equalityIDs.map{rows[$0]},weights:weights,prediction:prediction)
        let fallbackSolver=self""")
    source=once(source,'        for index in local {\n            let row=rows[index],variable=rowVariables[index]!\n            rhs[variable] = -row.residual',"""        // Same rank-one H for equality solve and direct KKT fallback; no RHS/row change.
        for term in woodTerms {
            let r=term.rope,i=term.first,b=term.vector,k=term.scale
            var indices:[Int]=[],values:[Double]=[]
            for endpoint in 0..<2 {for axis in 0..<3 {
                let v=variables[r][i+endpoint][axis]
                if v>=0 {indices.append(v);values.append(b[3*endpoint+axis])}
            }}
            try WoodMajorizerAssembly.add(system:&system,columns:&columns,border:&border,
                indices:indices,values:values,height:b[6],scale:k)
        }
        for index in local {
            let row=rows[index],variable=rowVariables[index]!
            rhs[variable] = -row.residual""")
    source=once(source,'"strain":maximumStrain(),"rows":rows.count,',
        '"strain":maximumStrain(),"rows":rows.count,"woodTerms":woodTerms.count,')
    source+='\n'+Path(__file__).with_name('Solver.swift.txt').read_text()
    return source

def driver_source(source,checkpoint=109):
    source=arrival_driver(source,140 if checkpoint==140 else 109)
    source=source.replace('arrivalStopExperiment','woodMajorizerExperiment').replace('"guardedArrivalStop":true','"woodMajorizer":true')
    source=once(source,'    try fixtures();result["fixturesPass"]=true','    try majorizerIntegrationFixtures();try majorizerFixtures();try fixtures();result["fixturesPass"]=true')
    if checkpoint==3:
        source=once(source,'for step in 1...108','for step in 1...2')
        source=once(source,'result["prefixIdentitySteps"]=108','result["prefixIdentitySteps"]=2')
        source=once(source,'"step":109]','"step":3]')
        source=once(source,'candidate.reviewStepCorrections<=5','candidate.reviewStepCorrections<=original.reviewStepCorrections')
        source=once(source,'guard median<=0.80','guard median<=1.10')
        source=source.replace('fixed <=5-QP work gate','fixed no-QP-increase work gate')
    source=source.replace('PASS Armijo fixtures','PASS wood-majorizer fixtures')
    source=source.replace('isolated step109',f'isolated wood-majorizer step{checkpoint}').replace('isolated step140',f'isolated wood-majorizer step{checkpoint}')
    return source

def trajectory_source(source):
    from arrival_stop.snapshot import trajectory_source as arrival_trajectory
    source=arrival_trajectory(source)
    source=source.replace('arrivalStopExperiment','woodMajorizerExperiment').replace('"guardedArrivalStop":true','"woodMajorizer":true')
    source=once(source,'do {\n    for step', 'do {\n    try majorizerFixtures();try majorizerIntegrationFixtures();result["fixturesPass"]=true\n    for step')
    return source
