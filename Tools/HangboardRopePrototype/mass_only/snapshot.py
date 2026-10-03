"""Candidate-only mass Hessian; every force/constraint/acceptance stays original."""
from armijo.snapshot import once


def solver_source(source):
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var massOnlyExperiment=false')
    source=once(source,'let stiffness=max(0,distanceTension[r][i])/length',
        'let stiffness=try RopeMassOnly.stiffness(max(0,distanceTension[r][i])/length,enabled:massOnlyExperiment)')
    return source


def driver_source(source):
    source=once(source,'var control=initial,candidate=initial,records:[[String:Any]]=[]',
        'var control=initial,candidate=initial,records:[[String:Any]]=[]\ncandidate.massOnlyExperiment=true\ntry massOnlyFixtures()')
    source=once(source,'"controlHz":240,"preflight":preflight,"armijoEnabled":false]',
        '"controlHz":240,"preflight":preflight,"armijoEnabled":false,"massOnly":true]')
    source=once(source,'        if hz==240 {','        if hz==240 && !candidate.massOnlyExperiment {')
    source=once(source,'    if !preflight {guard settledPhases.count==2', '''    let candidateQPs=records.reduce(0){$0+($1["candidateQPs"] as! Int)},controlQPs=records.reduce(0){$0+($1["controlQPs"] as! Int)}
    result["candidateQPs"]=candidateQPs;result["controlQPs"]=controlQPs
    try persist()
    guard candidateQPs<=controlQPs else {throw RopePhysicsError.invalid("mass-only total QP work gate")}
    if !preflight {guard settledPhases.count==2''')
    return source
