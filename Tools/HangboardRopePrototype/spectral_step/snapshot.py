"""Isolated inverse-secant step selection; original merit and integration."""
from armijo.snapshot import once


def solver_source(source):
    source=once(source,'    var armijoExperiment=false','''    var armijoExperiment=false
    var spectralStepExperiment=false
    private var spectralPoint:[Double]?=nil
    private var spectralDirection:[Double]?=nil
    private var spectralFullProbe=false
    private var spectralIteration=0''')
    source=once(source,'        let prediction=state\n        cachedEvaluation=nil','''        let prediction=state
        spectralPoint=nil;spectralDirection=nil;spectralFullProbe=false;spectralIteration=0
        cachedEvaluation=nil''')
    source=once(source,'        let penalty=max(1,2*(lambda.map{abs($0)}.max() ?? 0))','''        var spectralCurrent:[Double]=[],spectralRaw:[Double]=[]
        var spectralOmega:Double?=nil
        let trustAlpha=alpha
        if spectralStepExperiment {
            spectralIteration += 1
            for r in state.ropes.indices {for i in state.ropes[r].positions.indices where weights[r][i]>0 {
                let p=state.ropes[r].positions[i],d=corrections[r][i]
                spectralCurrent += [p.x,p.y,p.z];spectralRaw += [d.x,d.y,d.z]
            }}
            spectralCurrent.append(state.boardHeight);spectralRaw.append(heightCorrection)
            if spectralIteration>=3,!spectralFullProbe,let previousPoint=spectralPoint,let previousDirection=spectralDirection,
               let omega=RopeSpectralStep.relaxation(point:spectralCurrent,previousPoint:previousPoint,
                    direction:spectralRaw,previousDirection:previousDirection),omega<alpha {
                alpha=omega;spectralOmega=omega
            }
        }
        let penalty=max(1,2*(lambda.map{abs($0)}.max() ?? 0))''')
    source=once(source,'"strain":maximumStrain(),"rows":rows.count,"slope":armijoSlope as Any? ?? NSNull(),','''"strain":maximumStrain(),"rows":rows.count,
                        "trustAlpha":trustAlpha,"spectralOmega":spectralOmega as Any? ?? NSNull(),
                        "forcedFullProbe":spectralFullProbe,"slope":armijoSlope as Any? ?? NSNull(),''')
    source=once(source,'                    lastCorrectionFullStep=alpha==1','''                    if spectralStepExperiment {
                        // Only accepted states enter history; preserve the raw QP direction.
                        spectralPoint=spectralCurrent;spectralDirection=spectralRaw
                        spectralFullProbe=spectralOmega != nil
                    }
                    lastCorrectionFullStep=alpha==1''')
    return source


def driver_source(source,checkpoint=109):
    source=source.replace('candidate.armijoExperiment=true','candidate.spectralStepExperiment=true').replace('b.armijoExperiment=true','b.spectralStepExperiment=true')
    source=once(source,'    try fixtures();result["fixturesPass"]=true','    try spectralFixtures();try fixtures();result["fixturesPass"]=true;result["spectralStep"]=true')
    if checkpoint==140:
        source=once(source,'for step in 1...108','for step in 1...139')
        source=once(source,'result["prefixIdentitySteps"]=108','result["prefixIdentitySteps"]=139')
        source=once(source,'candidate.reviewStepCorrections<=5','candidate.reviewStepCorrections<=2')
        source=source.replace('fixed <=5-QP work gate','fixed <=2-QP ordinary-step work gate')
        source=once(source,'"step":109]','"step":140]')
        source=once(source,'guard median<=0.80','guard median<=1.10')
        source=source.replace('fixed median <=0.80 speed gate','fixed median <=1.10 ordinary-step overhead gate')
        source=source.replace('isolated step109','isolated step140')
    return source


def trajectory_source(source):
    source=once(source,'var control=initial,candidate=initial,records:[[String:Any]]=[]','var control=initial,candidate=initial,records:[[String:Any]]=[]\ncandidate.spectralStepExperiment=true\ntry spectralFixtures()')
    source=once(source,'        if hz==240 {','        if hz==240 && !candidate.spectralStepExperiment {')
    source=once(source,'"controlHz":240,"preflight":preflight,"armijoEnabled":false]','"controlHz":240,"preflight":preflight,"armijoEnabled":false,"spectralStep":true]')
    return source
