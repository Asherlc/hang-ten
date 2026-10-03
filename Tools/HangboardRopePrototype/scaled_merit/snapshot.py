"""Native-only force-scaled merit; original physics and integration retained."""
from armijo.snapshot import once


def solver_source(source):
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var scaledMeritExperiment=false\n    private var stepMeritPenalty=0.0')
    source=once(source,'        let prediction=state\n        cachedEvaluation=nil','        let prediction=state\n        stepMeritPenalty=0\n        cachedEvaluation=nil')
    source=once(source,'        let penalty=max(1,2*(lambda.map{abs($0)}.max() ?? 0))','''        let equalityMax=zip(selected,lambda).filter{!$0.0.contact}.map{abs($0.1)}.max() ?? 0
        let contactSum=zip(selected,lambda).filter{$0.0.contact}.reduce(0.0){$0+abs($1.1)}
        if scaledMeritExperiment {stepMeritPenalty=try RopeScaledMerit.next(previous:stepMeritPenalty,multipliers:lambda,contacts:selected.map{$0.contact})}
        let penalty=scaledMeritExperiment ? stepMeritPenalty:max(1,2*(lambda.map{abs($0)}.max() ?? 0))''')
    source=once(source,'        var armijoRejected=0,originalRejected=0','        let beforeParts=cachedEvaluation?.meritParts\n        var armijoRejected=0,originalRejected=0')
    source=once(source,'"strain":maximumStrain(),"rows":rows.count,"slope":armijoSlope as Any? ?? NSNull(),','''"strain":maximumStrain(),"rows":rows.count,"penalty":penalty,
                        "equalityMultiplierMax":equalityMax,"contactMultiplierSum":contactSum,
                        "beforeObjective":beforeParts?.0 as Any? ?? NSNull(),"beforeViolation":beforeParts?.1 as Any? ?? NSNull(),
                        "afterObjective":cachedEvaluation?.meritParts?.0 as Any? ?? NSNull(),"afterViolation":cachedEvaluation?.meritParts?.1 as Any? ?? NSNull(),
                        "slope":armijoSlope as Any? ?? NSNull(),''')
    return source


def driver_source(source):
    source=source.replace('candidate.armijoExperiment=true','candidate.scaledMeritExperiment=true').replace('b.armijoExperiment=true','b.scaledMeritExperiment=true')
    source=once(source,'    try fixtures();result["fixturesPass"]=true','    try scaledMeritFixtures();try fixtures();result["fixturesPass"]=true;result["scaledMerit"]=true')
    return source
