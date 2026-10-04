"""Fresh nonlinear residual, old KKT preconditioner; no affine certificate claim."""
from armijo.snapshot import once

def solver_source(source):
    source=once(source,'    var woodFeatureIdentityExperiment=false',
        '    var woodFeatureIdentityExperiment=false\n    var preconditionedResidualExperiment=false')
    source=once(source,'    static var stops=0','    static var stops=0\n    static var estimates:[Double]=[]')
    source=once(source,'                    if ResidualStopTrace.enabled && convergenceExperiment && alpha==1,','                    if ResidualStopTrace.enabled && convergenceExperiment && alpha==1,')
    source=once(source,'        // Apply the original affine inactive separation tolerance to every fresh row.',
        '        // Previous operator is a preconditioner only; selected affine consistency is experimental.\n        // Inactive fresh-row separation, compression and exact correspondence remain required.\n        // Apply the original affine inactive separation tolerance to every fresh row.')
    assert source.count('guard abs(value-1e-8*multiplier)<=1e-8 else{return nil}')==2
    source=source.replace('guard abs(value-1e-8*multiplier)<=1e-8 else{return nil}',
        'if !preconditionedResidualExperiment {guard abs(value-1e-8*multiplier)<=1e-8 else{return nil}}')
    return once(source,'        ResidualStopTrace.eligible += 1\n        return maximum',
        '        guard maximum.isFinite else{return nil}\n        if preconditionedResidualExperiment {ResidualStopTrace.estimates.append(maximum)}\n        ResidualStopTrace.eligible += 1\n        return maximum')

def driver_source(source,enabled=True):
    source=source.replace('candidate.woodFeatureIdentityExperiment=true',
        'candidate.woodFeatureIdentityExperiment=true;candidate.preconditionedResidualExperiment='+str(enabled).lower())
    source=source.replace('b.woodFeatureIdentityExperiment=true',
        'b.woodFeatureIdentityExperiment=true;b.preconditionedResidualExperiment='+str(enabled).lower())
    source=once(source,'ResidualStopTrace.stops=0','ResidualStopTrace.stops=0;ResidualStopTrace.estimates=[]')
    source=once(source,'    result["candidateResidualEligible"]=ResidualStopTrace.eligible;',
        '    result["candidateResidualEstimates"]=ResidualStopTrace.estimates\n    result["candidateResidualEligible"]=ResidualStopTrace.eligible;')
    return once(source,'"woodFeatureIdentity":true','"woodFeatureIdentity":true,"preconditionedResidual":'+str(enabled).lower()+',"freshSelectedAffineCertificate":false,"freshInactiveAffineSeparation":true')


def trajectory_source(source):
    source=once(source,'var control=initial,candidate=initial,records:[[String:Any]]=[]',
        'var control=initial,candidate=initial,records:[[String:Any]]=[]\ncandidate.woodMajorizerExperiment=true;candidate.woodResidualExperiment=true;candidate.woodFeatureIdentityExperiment=true;candidate.preconditionedResidualExperiment=true')
    source=once(source,'    ArmijoTrace.collectDerivatives=false;',
        '    ResidualStopTrace.enabled=x.woodResidualExperiment;ResidualStopTrace.eligible=0;ResidualStopTrace.stops=0;ResidualStopTrace.estimates=[]\n    ArmijoTrace.collectDerivatives=false;')
    source=once(source,'guard candidate.reviewStepCaps==0,candidate.reviewStepRetries==0,difference(control,candidate)<=0.00005 else {',
        'guard candidate.reviewStepCaps==0,candidate.reviewStepRetries==0,controlCaps==0,controlRetries==0,difference(control,candidate)<=0.00005 else {')
    source=once(source,'        if hz==240 {','        if hz==240 && !candidate.preconditionedResidualExperiment {')
    source=once(source,'if !preflight,measured.2.settled,!settledPhases.contains(phase) {','if !preflight,measured.2.settled {')
    source=once(source,'"controlHz":240,"preflight":preflight,"armijoEnabled":false]',
        '"controlHz":240,"preflight":preflight,"armijoEnabled":false,"preconditionedResidual":true,"freshSelectedAffineCertificate":false,"freshInactiveAffineSeparation":true]')
    source=once(source,'do {\n    for step','do {\n    try woodFeatureFixtures();try majorizerFixtures();try majorizerIntegrationFixtures();result["fixturesPass"]=true\n    for step')
    return source
