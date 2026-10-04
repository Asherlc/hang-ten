"""Narrower wood discovery, same100um clearance target; copied sources only."""
from armijo.snapshot import once
from pathlib import Path

PRIOR='.context/strong-owl-live-physics-armijo-b4c2027fc-preconditioned-stop-540/native/result.json'

def solver_source(s):
    s=once(s,'    var preconditionedResidualExperiment=false',
        '    var preconditionedResidualExperiment=false\n    var woodWindowExperiment=false\n    private var woodQueryLookahead:Double {woodWindowExperiment ? 0.00001:0.00005}')
    assert s.count('residual:0.00005-hit.penetrationDepth')==2
    s=s.replace('residual:0.00005-hit.penetrationDepth','residual:woodQueryLookahead-hit.penetrationDepth')
    s=once(s,'rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005','rowRadius:rope.radius+RopeRegionGeometry.clearance+woodQueryLookahead')
    s=once(s,'        var portalOrder:[String]=[]','        bits.append(woodQueryLookahead.bitPattern)\n        var portalOrder:[String]=[]')
    s=once(s,'clearanceReceipts:receipts,clearanceObserver:','clearanceReceipts:receipts,woodQueryLookahead:woodQueryLookahead,clearanceObserver:')
    return once(s,'            clearances.append(batch.clearances)',
        '            if NarrowDiscoveryTrace.capture {NarrowDiscoveryTrace.faces += batch.faceVisits}\n            clearances.append(batch.clearances)')

def metrics_source(s):
    s=once(s,'clearanceReceipts:[[Double?]]?=nil,clearanceObserver:',
        'clearanceReceipts:[[Double?]]?=nil,woodQueryLookahead:Double=0.00005,clearanceObserver:')
    s=once(s,'let lowerBound=rope.radius+RopeRegionGeometry.clearance+0.00005',
        'let lowerBound=rope.radius+RopeRegionGeometry.clearance+woodQueryLookahead')
    assert s.count('segmentClearance=collider.segmentClearance(from:a,to:b)')==2
    s=s.replace('segmentClearance=collider.segmentClearance(from:a,to:b)',
        'if NarrowDiscoveryTrace.capture {NarrowDiscoveryTrace.fallbackQueries += 1};segmentClearance=collider.segmentClearance(from:a,to:b)')
    return s

def collider_source(s):
    start=s.index('    func fusedContactEvaluation(');end=s.index('    private struct FusedWitness',start)
    original=s[start:end]
    control=original.replace('func fusedContactEvaluation(', 'private func wideWindowControl(')
    s=s[:end]+control+s[end:]
    assert s.count('clearance:Double?)')==3
    s=s.replace('clearance:Double?)','clearance:Double?,faceVisits:Int)')
    assert s.count('radius:rowRadius)],nil)')==2
    s=s.replace('radius:rowRadius)],nil)','radius:rowRadius)],nil,0)')
    assert s.count('return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum)')==2
    s=s.replace('return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum)',
        'return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum,faces.count)')
    s=once(s,'results.initialize(repeating:([],nil),count:linkCount)','results.initialize(repeating:([],nil,0),count:linkCount)')
    s=once(s,'clearances:[Double?]) {','clearances:[Double?],faceVisits:Int) {')
    s=once(s,'        return (p,r,m,clearances)','        return (p,r,m,clearances,(0..<links).reduce(0){$0+storage.results[$1].faceVisits})')
    # Validation uses original wider search, but exactly the same merit cutoff.
    marker='        return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum,faces.count)'
    first=s.index(marker,start)
    s=s[:first]+"""        if NarrowDiscoveryTrace.verifyMerit {
            let control=wideWindowControl(from:start,to:end,rowRadius:rowRadius+0.00004,meritRadius:meritRadius,startInside:startInside,endInside:endInside)
            precondition(control.hits[2].count==meritHits.count,"narrow merit count")
            for (a,b) in zip(control.hits[2],meritHits) {
                precondition(a.centerlinePoint==b.centerlinePoint && a.surfacePoint==b.surfacePoint && a.normal==b.normal && a.fraction.bitPattern==b.fraction.bitPattern && a.penetrationDepth.bitPattern==b.penetrationDepth.bitPattern && a.sourceFeature==b.sourceFeature,"narrow merit witness")
            }
        }
"""+s[first:]
    s=once(s,'    let values:UnsafeMutablePointer<Bool>','    let queries:UnsafeMutablePointer<Int>?\n    let values:UnsafeMutablePointer<Bool>')
    s=once(s,'init(_ count:Int) {self.count=count;','init(_ count:Int) {queries=NarrowDiscoveryTrace.capture ? .allocate(capacity:count):nil;queries?.initialize(repeating:0,count:count);self.count=count;')
    s=once(s,'    deinit {values.deinitialize','    deinit {queries?.deinitialize(count:count);queries?.deallocate();values.deinitialize')
    s=once(s,'                output.values[i]=sweptSegmentContact','                output.queries?[i]=1\n                output.values[i]=sweptSegmentContact')
    s=once(s,'        return (0..<links).allSatisfy{output.values[$0]}',
        '        if let queries=output.queries {NarrowDiscoveryTrace.ccdQueries += (0..<links).reduce(0){$0+queries[$1]}}\n        return (0..<links).allSatisfy{output.values[$0]}')
    return s

def driver_source(s):
    s=once(s,'let prior=try decodeCheckpointJSON(Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2])))',
        'let prior=try decodeCheckpointJSON(Data(contentsOf:URL(fileURLWithPath:"'+PRIOR+'")))')
    s=once(s,'    for step in 1...139 {',
        '    initial.woodMajorizerExperiment=true;initial.woodResidualExperiment=true;initial.woodFeatureIdentityExperiment=true;initial.preconditionedResidualExperiment=true\n    for step in 1...139 {')
    s=once(s,'let old=(priorSteps[step-1]["trace"] as! [String:Any])["corrections"] as! [[String:Double]]',
        'let old=priorSteps[step-1]["trace"] as! [[String:Any]]')
    s=once(s,'guard (a[key] as! Double)==b[key] else','guard (a[key] as! Double)==(b[key] as! Double) else')
    s=s.replace('candidate.preconditionedResidualExperiment=true','candidate.preconditionedResidualExperiment=true;candidate.woodWindowExperiment=true')
    s=s.replace('b.preconditionedResidualExperiment=true','b.preconditionedResidualExperiment=true;b.woodWindowExperiment=true')
    s=once(s,'    let control=try run(&original),probe=try run(&candidate)',
        '    NarrowDiscoveryTrace.capture=true;NarrowDiscoveryTrace.verifyMerit=true\n    let control=try run(&original)\n    result["controlWork"]=["faces":NarrowDiscoveryTrace.faces,"fallbackQueries":NarrowDiscoveryTrace.fallbackQueries,"ccdQueries":NarrowDiscoveryTrace.ccdQueries]\n    let probe=try run(&candidate)\n    result["candidateWork"]=["faces":NarrowDiscoveryTrace.faces,"fallbackQueries":NarrowDiscoveryTrace.fallbackQueries,"ccdQueries":NarrowDiscoveryTrace.ccdQueries]\n    NarrowDiscoveryTrace.capture=false;NarrowDiscoveryTrace.verifyMerit=false')
    s=once(s,'    ArmijoTrace.collectDerivatives=x.armijoExperiment',
        '    NarrowDiscoveryTrace.reset()\n    ArmijoTrace.collectDerivatives=x.armijoExperiment')
    s=once(s,'guard median<=0.80','guard median<=0.85')
    s=s.replace('fixed median <=0.80 physical-residual speed gate','fixed median <=0.85 narrow-discovery speed gate')
    return once(s,'"preconditionedResidual":true','"preconditionedResidual":true,"woodDiscoveryLookahead":0.00001,"sameClearanceTarget":true,"propagatedPreconditionedInput":true')
