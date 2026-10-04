"""Exact shared native wood feature keys for the separately registered residual screen."""
from armijo.snapshot import once
from wood_residual import snapshot as residual

def solver_source(source):
    source=residual.solver_source(source)
    source=once(source,'    var woodResidualExperiment=false','    var woodResidualExperiment=false\n    var woodFeatureIdentityExperiment=false')
    for kind in ['point','link']:
        original='hit.sourceFeature.map{"wood-'+kind+'/\\(r)/\\(i)/\\($0.x)/\\($0.y)"}'
        canonical='hit.sourceFeature.flatMap {feature in WoodFeatureIdentity.key(faceID:feature.x,face:collider.mesh.triangles[feature.x],source:feature.y,fraction:hit.fraction).map{"wood-'+kind+'/\\(r)/\\(i)/\\($0)"}}'
        source=once(source,original,'woodFeatureIdentityExperiment ? ('+canonical+'):('+original+')')
    return source

def driver_source(source,checkpoint=140,enabled=True):
    source=residual.driver_source(source,checkpoint,True)
    source=source.replace('candidate.woodResidualExperiment=true',f'candidate.woodResidualExperiment=true;candidate.woodFeatureIdentityExperiment={str(enabled).lower()}')
    source=source.replace('b.woodResidualExperiment=true',f'b.woodResidualExperiment=true;b.woodFeatureIdentityExperiment={str(enabled).lower()}')
    source=once(source,'    try majorizerIntegrationFixtures();try majorizerFixtures();try fixtures();','    try woodFeatureFixtures();try majorizerIntegrationFixtures();try majorizerFixtures();try fixtures();')
    source=once(source,'"woodResidual":true','"woodResidual":true,"woodFeatureIdentity":'+str(enabled).lower())
    return source
