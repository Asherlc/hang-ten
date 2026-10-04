"""One attribution-only run; original result and one-QP failure must remain unchanged."""
from armijo.snapshot import once

def solver_source(source):
    replacements=[
        ('guard let context=residualContext else{return nil}','context-absent'),
        ('do {fresh=try buildConstraintRows(prediction:prediction)} catch {return nil}','fresh-row-build'),
        ('guard let source=old.sourceID,let found=buckets[source],found.count==1 else{return nil}','source-correspondence'),
        ('row.contact==old.contact,row.lengthSegment==old.lengthSegment else{return nil}','binding-change'),
        ('guard Set(ids).count==ids.count else{return nil}','duplicate-mapped-row'),
        ('guard let v=context.rowVariables[k] else{return nil}','equality-slot'),
        ('do {estimated=try context.factor.solve(rhs:rhs,borderRHS:borderRHS,contactResiduals:contactResiduals)} catch{return nil}','factor-solve'),
        ('guard multiplier.isFinite,multiplier<=0 else{return nil}','updated-compression'),
        ('guard value.isFinite else{return nil}','nonfinite-affine'),
        ('guard abs(value-1e-8*multiplier)<=1e-8 else{return nil}','affine-gap'),
        ('} else if value < -1e-8 {return nil}','inactive-affine-gap'),
        ('guard let k=ids.prefix(eqCount).firstIndex(of:id),let v=context.rowVariables[k] else{return nil}','fresh-equality-slot')]
    for old,reason in replacements:
        count=2 if reason=='affine-gap' else 1
        assert source.count(old)==count,(reason,source.count(old))
        source=source.replace(old,old.replace('return nil',f'ResidualDiagnostic.record("{reason}");return nil'))
    marker='ResidualDiagnostic.record("source-correspondence");return nil'
    source=once(source,marker,"""ResidualDiagnostic.record("source-correspondence")
                if ResidualDiagnostic.enabled {
                    let candidates=rows.filter{$0.rope==old.rope && $0.particles==old.particles && $0.contact==old.contact}
                    ResidualDiagnostic.correspondence.append(["oldSource":old.sourceID as Any? ?? NSNull(),
                        "particles":old.particles,"rope":old.rope,
                        "freshSources":candidates.map{$0.sourceID as Any? ?? NSNull()},
                        "oldGradients":old.gradients.map{[$0.x,$0.y,$0.z]},
                        "freshGradients":candidates.map{$0.gradients.map{[$0.x,$0.y,$0.z]}}])
                }
                return nil""")
    source+="""
enum ResidualDiagnostic {
    static var enabled=false
    static var counts:[String:Int]=[:]
    static var correspondence:[[String:Any]]=[]
    static func record(_ reason:String) {if enabled {counts[reason,default:0] += 1}}
}
"""
    return source

def driver_source(source):
    source=once(source,'    let control=try run(&original),probe=try run(&candidate)',
        '    var uninstrumented=candidate\n    ResidualDiagnostic.enabled=false\n    _ = try run(&uninstrumented)\n    ResidualDiagnostic.enabled=true;ResidualDiagnostic.counts=[:]\n    let control=try run(&original),probe=try run(&candidate)')
    source=once(source,'    result["candidateResidualEligible"]=ResidualStopTrace.eligible;',
        '    result["residualRejectionReasons"]=ResidualDiagnostic.counts\n    result["correspondenceDetails"]=ResidualDiagnostic.correspondence\n    result["completeInstrumentationIdentity"]=try serialize(candidate.bundleCheckpoint())==serialize(uninstrumented.bundleCheckpoint())\n    guard try serialize(candidate.bundleCheckpoint())==serialize(uninstrumented.bundleCheckpoint()) else{throw RopePhysicsError.invalid("instrumentation altered complete checkpoint")}\n    result["candidateResidualEligible"]=ResidualStopTrace.eligible;')
    return source
