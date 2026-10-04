"""Separate composed native experiment: positive wood curvature + physical residual stopping."""
from pathlib import Path
from armijo.snapshot import once
from residual_stop import snapshot as residual
from wood_majorizer import snapshot as majorizer

def contact_source(source):
    source=residual.contact_source(source)
    # Capture only when explicitly enabled for this candidate run, not controls/strict references.
    old='residualOperator:ResidualOperator(factor:factor,rows:active.map{contacts[$0]},responses:try active.map{try response($0)},lower:cholesky.lower))'
    source=once(source,old,'residualOperator:ResidualStopTrace.enabled ? ResidualOperator(factor:factor,rows:active.map{contacts[$0]},responses:try active.map{try response($0)},lower:cholesky.lower):nil)')
    return source

def collider_source(source):
    source=residual.collider_source(source)
    source=once(source,'    var timeOfImpact: Double? = nil','    var timeOfImpact: Double? = nil\n    var woodFaceIndex:Int?=nil')
    source=once(source,'sourceFeature:SIMD2(faceIndex,source))','sourceFeature:SIMD2(faceIndex,source),woodFaceIndex:faceIndex)')
    for marker,count in [('private static func triangleClosestSource',1),('func segmentPairSource',1),('let (q,branch)=Self.triangleClosestSource',2),('Self.segmentPairSource(start,end,',3),('sourceFeature:SIMD2(faceIndex,source),woodFaceIndex:faceIndex)',1)]:
        assert source.count(marker)==count,(marker,source.count(marker))
    return source+'\n'+Path(majorizer.__file__).with_name('Selection.swift.txt').read_text()

def solver_source(source):
    source=residual.solver_source(source)
    source=majorizer.solver_source(source)
    source=once(source,'let armijoSlope=armijoExperiment ? armijoDirectionalDerivative(evaluation:evaluation,prediction:prediction,\n            weights:weights,corrections:corrections,height:heightCorrection,penalty:penalty):nil',
        'let armijoSlope:Double?=nil // This isolated screen always uses the original merit.')
    source=once(source,'    var woodMajorizerExperiment=false','    var woodMajorizerExperiment=false\n    var woodResidualExperiment=false\n    private var residualStopAccepted=false')
    source=once(source,'    private mutating func correctConstraints(prediction:RopeSimulationState) throws -> Double {',
        '    private mutating func correctConstraints(prediction:RopeSimulationState) throws -> Double {\n        residualStopAccepted=false')
    source=once(source,'if maximumStrain()<0.0002 && estimate<limit {ResidualStopTrace.stops += 1;return estimate}',
        'if physicalResidualFeasible() && estimate<limit {residualStopAccepted=true;ResidualStopTrace.stops += 1;return estimate}')
    source=once(source,'            if maximumStrain()<0.0002 && movement<limit &&',
        '            if (maximumStrain()<0.0002 || (woodResidualExperiment && residualStopAccepted)) && movement<limit &&')
    source+="""
extension RopeDynamicsSolver {
    private func physicalResidualFeasible()->Bool {
        guard maximumStrain()<=0.005 else{return false}
        for rope in state.ropes {
            var length=0.0
            for i in rope.restLengths.indices {length += simd_distance(rope.positions[i],rope.positions[i+1])}
            guard abs(length-rope.restLengths.reduce(0,+))<=0.0005 else{return false}
        }
        return true
    }
}
"""
    for marker,count in [('private mutating func buildConstraintRows',1),('woodHit:hit',1),('woodResidualExperiment && residualStopAccepted',1),('physicalResidualFeasible() && estimate<limit',1),('residualContext=ResidualContext',1)]:
        assert source.count(marker)==count,(marker,source.count(marker))
    return source

def driver_source(source,checkpoint=140,enabled=True):
    source=majorizer.driver_source(source,checkpoint)
    source=source.replace('candidate.woodMajorizerExperiment=true',f'candidate.woodMajorizerExperiment=true;candidate.woodResidualExperiment={str(enabled).lower()}')
    source=source.replace('b.woodMajorizerExperiment=true',f'b.woodMajorizerExperiment=true;b.woodResidualExperiment={str(enabled).lower()}')
    source=once(source,'    ArmijoTrace.collectDerivatives=x.armijoExperiment',
        '    ResidualStopTrace.enabled=x.woodResidualExperiment;ResidualStopTrace.eligible=0;ResidualStopTrace.stops=0\n    ArmijoTrace.collectDerivatives=x.armijoExperiment')
    source=once(source,'    result["candidateMetrics"]=try check(candidate)',
        '    result["candidateResidualEligible"]=ResidualStopTrace.eligible;result["candidateResidualStops"]=ResidualStopTrace.stops\n    result["candidateMetrics"]=try check(candidate)')
    source=once(source,'"woodMajorizer":true','"woodMajorizer":true,"woodResidual":'+str(enabled).lower())
    if checkpoint==140:
        source=once(source,'candidate.reviewStepCorrections<=2','candidate.reviewStepCorrections<=1')
        source=source.replace('fixed <=2-QP ordinary-step work gate','fixed <=1-QP physical-residual work gate')
        source=once(source,'guard median<=1.10','guard median<=0.80')
    return source
